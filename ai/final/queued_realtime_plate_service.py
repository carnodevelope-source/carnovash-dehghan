"""Queued, batched, session-aware plate and vehicle-color inference service."""

from __future__ import annotations

import queue
import threading
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
import torch

from predict import (
    DEVICE,
    _expand,
    _models,
    _read_color_details,
    _read_plate_details,
    _rectify_plate,
)


@dataclass
class SessionState:
    frame_index: int = 0
    last_thumb: Optional[np.ndarray] = None
    last_bbox: Optional[Tuple[int, int, int, int]] = None
    last_raw_text: str = ""
    last_persian_text: str = ""
    last_confidence: float = 0.0
    last_detector_confidence: float = 0.0
    last_ocr_frame: int = -10_000
    votes: Counter = field(default_factory=Counter)
    stable_text: str = ""
    stable_persian_text: str = ""
    last_color: str = "unknown"
    last_color_confidence: float = 0.0
    last_color_reliable: bool = False
    last_color_frame: int = -10_000
    color_votes: Counter = field(default_factory=Counter)
    stable_color: str = ""


@dataclass
class FrameRequest:
    session_id: str
    frame_bgr: np.ndarray
    enqueue_time: float
    response_queue: queue.Queue
    force_process: bool = False


class QueuedRealtimePlateService:
    """Drop-in compatible with ai/QueuedRealtimePlateService, plus color fields."""

    def __init__(
        self,
        detector_weights: str | None = None,
        recognizer_weights: str | None = None,
        detector_imgsz: int = 640,
        threshold: float = 0.30,
        max_detections: int = 4,
        keyframe_interval: int = 4,
        ocr_interval: int = 12,
        color_interval: int = 18,
        stable_hits: int = 2,
        thumb_diff_threshold: float = 2.0,
        min_box_area: int = 300,
        max_batch_size: int = 8,
        batch_wait_ms: int = 12,
        max_queue_size: int = 256,
    ):
        del detector_weights, recognizer_weights, keyframe_interval
        self.device = DEVICE
        self.use_half = DEVICE == "cuda"
        self.detector_imgsz = detector_imgsz
        self.threshold = threshold
        self.max_detections = max_detections
        self.ocr_interval = max(1, ocr_interval)
        self.color_interval = max(1, color_interval)
        self.stable_hits = max(1, stable_hits)
        self.thumb_diff_threshold = thumb_diff_threshold
        self.min_box_area = min_box_area
        self.max_batch_size = max(1, max_batch_size)
        self.batch_wait_ms = max(0, batch_wait_ms)
        self.request_queue: queue.Queue = queue.Queue(maxsize=max_queue_size)
        self.sessions: Dict[str, SessionState] = {}
        self.metrics = {
            "device": DEVICE, "detector_imgsz": detector_imgsz, "submitted": 0,
            "dropped_queue_full": 0, "returned_without_gpu": 0,
            "detector_frames": 0, "ocr_runs": 0, "color_runs": 0,
            "gpu_batches": 0, "gpu_batch_items": 0,
        }
        # Load once and warm up before accepting traffic.
        models = _models()
        dummy = np.zeros((320, 640, 3), dtype=np.uint8)
        models.plate_detector.predict(dummy, imgsz=detector_imgsz, device=DEVICE, verbose=False)
        models.vehicle_detector.predict(dummy, imgsz=detector_imgsz, device=DEVICE, verbose=False)
        self._stop_event = threading.Event()
        self._worker = threading.Thread(target=self._worker_loop, name="plate-color-gpu-worker", daemon=True)
        self._worker.start()

    def shutdown(self):
        self._stop_event.set()
        self._worker.join(timeout=2.0)
        if torch.cuda.is_available(): torch.cuda.empty_cache()

    def submit_frame(self, session_id: str, frame_bgr: np.ndarray, timeout_sec: float = 5.0, force_process: bool = False) -> Dict:
        response_queue: queue.Queue = queue.Queue(maxsize=1)
        request = FrameRequest(session_id, frame_bgr, time.perf_counter(), response_queue, force_process)
        self.metrics["submitted"] += 1
        try:
            self.request_queue.put_nowait(request)
        except queue.Full:
            self.metrics["dropped_queue_full"] += 1
            return {"accepted": False, "reason": "queue_full", "latency_ms": 0.0, "queue_depth": self.request_queue.qsize()}
        try:
            return response_queue.get(timeout=timeout_sec)
        except queue.Empty:
            return {"accepted": False, "reason": "timeout_waiting_for_worker", "latency_ms": timeout_sec * 1000.0, "queue_depth": self.request_queue.qsize()}

    def get_metrics(self) -> Dict:
        result = dict(self.metrics)
        result.update(queue_depth=self.request_queue.qsize(), session_count=len(self.sessions))
        result["avg_batch_size"] = result["gpu_batch_items"] / result["gpu_batches"] if result["gpu_batches"] else 0.0
        if torch.cuda.is_available():
            index = torch.cuda.current_device()
            result.update(
                gpu_used_mb=torch.cuda.memory_allocated(index) / 1024 ** 2,
                gpu_reserved_mb=torch.cuda.memory_reserved(index) / 1024 ** 2,
                gpu_peak_mb=torch.cuda.max_memory_allocated(index) / 1024 ** 2,
            )
        else:
            result.update(gpu_used_mb=0.0, gpu_reserved_mb=0.0, gpu_peak_mb=0.0)
        return result

    def _worker_loop(self):
        while not self._stop_event.is_set():
            try: first = self.request_queue.get(timeout=0.1)
            except queue.Empty: continue
            batch = [first]; deadline = time.perf_counter() + self.batch_wait_ms / 1000.0
            while len(batch) < self.max_batch_size:
                remaining = deadline - time.perf_counter()
                if remaining <= 0: break
                try: batch.append(self.request_queue.get(timeout=remaining))
                except queue.Empty: break
            try:
                self._process_batch(batch)
            except Exception as exc:
                for request in batch:
                    if request.response_queue.empty():
                        request.response_queue.put({"accepted": False, "reason": "inference_error", "detail": str(exc), "latency_ms": round((time.perf_counter() - request.enqueue_time) * 1000, 2), "queue_depth": self.request_queue.qsize()})

    def _process_batch(self, batch: List[FrameRequest]):
        active = []
        for request in batch:
            state = self.sessions.setdefault(request.session_id, SessionState()); state.frame_index += 1
            cached = self._precheck(state, request)
            if cached is not None:
                self.metrics["returned_without_gpu"] += 1; request.response_queue.put(cached)
            else: active.append((request, state))
        if not active: return
        frames = [item[0].frame_bgr for item in active]
        self.metrics["gpu_batches"] += 1; self.metrics["gpu_batch_items"] += len(frames); self.metrics["detector_frames"] += len(frames)
        plate_results = _models().plate_detector.predict(frames, conf=self.threshold, imgsz=self.detector_imgsz, device=DEVICE, max_det=self.max_detections, verbose=False, half=self.use_half, stream=False)

        color_jobs = []
        for result, (request, state) in zip(plate_results, active):
            self._process_plate(request.frame_bgr, state, result)
            if request.force_process or state.last_color == "unknown" or state.frame_index - state.last_color_frame >= self.color_interval:
                color_jobs.append((request, state))

        if color_jobs:
            color_frames = [item[0].frame_bgr for item in color_jobs]
            vehicle_results = _models().vehicle_detector.predict(color_frames, conf=0.22, imgsz=self.detector_imgsz, device=DEVICE, max_det=8, classes=[2, 3, 5, 7], verbose=False, half=self.use_half, stream=False)
            for result, (request, state) in zip(vehicle_results, color_jobs):
                crop = self._vehicle_crop(request.frame_bgr, result)
                details = _read_color_details(crop); self.metrics["color_runs"] += 1
                state.last_color = str(details["name"]); state.last_color_confidence = float(details["confidence"]); state.last_color_reliable = bool(details["reliable"]); state.last_color_frame = state.frame_index
                if state.last_color_reliable:
                    state.color_votes[state.last_color] += 1
                    if state.color_votes[state.last_color] >= self.stable_hits: state.stable_color = state.last_color

        for request, state in active:
            reason = "ocr_ran" if state.last_ocr_frame == state.frame_index else ("ocr_reused" if state.last_bbox else "no_plate")
            request.response_queue.put(self._response(state, request, True, reason))

    def _precheck(self, state: SessionState, request: FrameRequest) -> Optional[Dict]:
        thumb = self._thumb(request.frame_bgr)
        if request.force_process: state.last_thumb = thumb; return None
        if state.last_thumb is not None:
            diff = float(np.mean(cv2.absdiff(thumb, state.last_thumb)))
            if (state.last_raw_text or state.last_color != "unknown") and diff < self.thumb_diff_threshold:
                state.last_thumb = thumb
                return self._response(state, request, False, "duplicate_frame")
        state.last_thumb = thumb
        return None

    def _process_plate(self, frame: np.ndarray, state: SessionState, result):
        height, width = frame.shape[:2]; best = None
        if result.boxes is not None:
            for index in range(len(result.boxes)):
                box = _expand(result.boxes.xyxy[index].tolist(), width, height, 0.08)
                x1, y1, x2, y2 = box; area = max(0, x2 - x1) * max(0, y2 - y1); confidence = float(result.boxes.conf[index])
                score = confidence * np.sqrt(max(1, area))
                if area >= self.min_box_area and (best is None or score > best[0]): best = (score, box, confidence)
        if best is None:
            state.last_bbox = None; state.last_detector_confidence = 0.0
            state.last_raw_text = ""; state.last_persian_text = ""; state.last_confidence = 0.0
            state.votes.clear(); state.stable_text = ""; state.stable_persian_text = ""
            return
        state.last_bbox = best[1]; state.last_detector_confidence = best[2]
        if state.last_raw_text and state.frame_index - state.last_ocr_frame < self.ocr_interval: return
        x1, y1, x2, y2 = best[1]; crop = frame[y1:y2, x1:x2]
        if crop.size == 0: return
        details = _read_plate_details(_rectify_plate(crop)); self.metrics["ocr_runs"] += 1; state.last_ocr_frame = state.frame_index
        if details["status"] != "ok": return
        state.last_raw_text = str(details["latin"]); state.last_persian_text = str(details["persian"]); state.last_confidence = float(details["confidence"])
        state.votes[state.last_raw_text] += 1
        if state.votes[state.last_raw_text] >= self.stable_hits:
            state.stable_text = state.last_raw_text; state.stable_persian_text = state.last_persian_text

    @staticmethod
    def _vehicle_crop(frame: np.ndarray, result) -> np.ndarray:
        height, width = frame.shape[:2]; best = None
        if result.boxes is not None:
            for index in range(len(result.boxes)):
                box = _expand(result.boxes.xyxy[index].tolist(), width, height, 0.06)
                x1, y1, x2, y2 = box; area = max(1, (x2 - x1) * (y2 - y1)); confidence = float(result.boxes.conf[index]); score = confidence * np.sqrt(area)
                if best is None or score > best[0]: best = (score, box)
        if best:
            x1, y1, x2, y2 = best[1]; return frame[y1:y2, x1:x2]
        return frame[int(height * .03):int(height * .97), int(width * .04):int(width * .96)]

    def _response(self, state: SessionState, request: FrameRequest, processed: bool, reason: str) -> Dict:
        return {
            "accepted": True, "processed": processed, "reason": reason, "frame_index": state.frame_index,
            "bbox": state.last_bbox, "text": state.stable_text or state.last_raw_text,
            "persian_text": state.stable_persian_text or state.last_persian_text,
            "confidence": state.last_confidence, "detector_confidence": state.last_detector_confidence,
            "stable": bool(state.stable_text), "color": state.stable_color or state.last_color,
            "color_confidence": state.last_color_confidence, "color_reliable": state.last_color_reliable,
            "color_stable": bool(state.stable_color),
            "latency_ms": round((time.perf_counter() - request.enqueue_time) * 1000.0, 2),
            "queue_depth": self.request_queue.qsize(),
        }

    @staticmethod
    def _thumb(frame: np.ndarray) -> np.ndarray:
        return cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (16, 16), interpolation=cv2.INTER_AREA)
