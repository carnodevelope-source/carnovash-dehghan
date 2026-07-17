import argparse
import os
import queue
import threading
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
import torch
from ultralytics import YOLO

from deep_text_recognition_benchmark.dtrb import DTRB
from light_plate_common import DEFAULT_OCR_CHARACTER_SET, clamp_bbox, configure_torch_runtime, postprocess_plate_text


@dataclass
class SessionState:
    frame_index: int = 0
    last_thumb: Optional[np.ndarray] = None
    last_bbox: Optional[Tuple[int, int, int, int]] = None
    last_raw_text: str = ""
    last_persian_text: str = ""
    last_confidence: float = 0.0
    last_ocr_frame: int = -10_000
    votes: Counter = field(default_factory=Counter)
    stable_text: str = ""
    stable_persian_text: str = ""


@dataclass
class FrameRequest:
    session_id: str
    frame_bgr: np.ndarray
    enqueue_time: float
    response_queue: queue.Queue
    force_process: bool = False


def build_runtime_args():
    args = argparse.Namespace()
    args.workers = 0
    args.batch_size = 1
    args.batch_max_length = 25
    args.imgH = 32
    args.imgW = 100
    args.rgb = False
    args.character = DEFAULT_OCR_CHARACTER_SET
    args.sensitive = False
    args.PAD = False
    args.Transformation = "TPS"
    args.FeatureExtraction = "ResNet"
    args.SequenceModeling = "BiLSTM"
    args.Prediction = "Attn"
    args.num_fiducial = 20
    args.input_channel = 1
    args.output_channel = 512
    args.hidden_size = 256
    requested_device = os.getenv("PLATE_AI_DEVICE", "auto").strip().lower()
    if requested_device == "auto":
        requested_device = "cuda" if torch.cuda.is_available() else "cpu"
    args.device = requested_device
    args.half = requested_device == "cuda"
    default_cpu_threads = min(4, max(1, os.cpu_count() or 1))
    try:
        args.cpu_threads = max(1, int(os.getenv("PLATE_AI_CPU_THREADS", default_cpu_threads) or default_cpu_threads))
    except ValueError:
        args.cpu_threads = default_cpu_threads
    return args


class QueuedRealtimePlateService:
    def __init__(
        self,
        detector_weights: str,
        recognizer_weights: str,
        detector_imgsz: int = 416,
        threshold: float = 0.7,
        max_detections: int = 1,
        keyframe_interval: int = 4,
        ocr_interval: int = 12,
        stable_hits: int = 2,
        thumb_diff_threshold: float = 2.0,
        min_box_area: int = 800,
        max_batch_size: int = 8,
        batch_wait_ms: int = 12,
        max_queue_size: int = 256,
    ):
        self.args = build_runtime_args()
        configure_torch_runtime(self.args.device, self.args.cpu_threads)
        self.detector_device = self.args.device
        self.use_half = self.args.device == "cuda"
        self.detector = YOLO(detector_weights)
        self.recognizer = DTRB(recognizer_weights, self.args)
        self.detector_imgsz = detector_imgsz
        self.threshold = threshold
        self.max_detections = max_detections
        self.keyframe_interval = max(1, keyframe_interval)
        self.ocr_interval = max(1, ocr_interval)
        self.stable_hits = max(1, stable_hits)
        self.thumb_diff_threshold = thumb_diff_threshold
        self.min_box_area = min_box_area
        self.max_batch_size = max(1, max_batch_size)
        self.batch_wait_ms = max(0, batch_wait_ms)
        self.request_queue: queue.Queue = queue.Queue(maxsize=max_queue_size)
        self.sessions: Dict[str, SessionState] = {}
        self.metrics = {
            "device": self.args.device,
            "cpu_threads": self.args.cpu_threads,
            "detector_imgsz": self.detector_imgsz,
            "submitted": 0,
            "dropped_queue_full": 0,
            "returned_without_gpu": 0,
            "detector_frames": 0,
            "ocr_runs": 0,
            "gpu_batches": 0,
            "gpu_batch_items": 0,
        }
        self._stop_event = threading.Event()
        self._worker = threading.Thread(target=self._worker_loop, name="plate-gpu-worker", daemon=True)
        self._worker.start()

    def shutdown(self):
        self._stop_event.set()
        self._worker.join(timeout=2.0)
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def submit_frame(self, session_id: str, frame_bgr: np.ndarray, timeout_sec: float = 5.0, force_process: bool = False) -> Dict:
        response_queue: queue.Queue = queue.Queue(maxsize=1)
        request = FrameRequest(
            session_id=session_id,
            frame_bgr=frame_bgr,
            enqueue_time=time.perf_counter(),
            response_queue=response_queue,
            force_process=force_process,
        )
        self.metrics["submitted"] += 1

        try:
            self.request_queue.put_nowait(request)
        except queue.Full:
            self.metrics["dropped_queue_full"] += 1
            return {
                "accepted": False,
                "reason": "queue_full",
                "latency_ms": 0.0,
                "queue_depth": self.request_queue.qsize(),
            }

        try:
            return response_queue.get(timeout=timeout_sec)
        except queue.Empty:
            return {
                "accepted": False,
                "reason": "timeout_waiting_for_worker",
                "latency_ms": timeout_sec * 1000.0,
                "queue_depth": self.request_queue.qsize(),
            }

    def get_metrics(self) -> Dict:
        metrics = dict(self.metrics)
        metrics["queue_depth"] = self.request_queue.qsize()
        metrics["session_count"] = len(self.sessions)
        metrics["avg_batch_size"] = (
            metrics["gpu_batch_items"] / metrics["gpu_batches"] if metrics["gpu_batches"] else 0.0
        )
        if torch.cuda.is_available():
            device_index = torch.cuda.current_device()
            metrics["gpu_used_mb"] = torch.cuda.memory_allocated(device_index) / (1024 ** 2)
            metrics["gpu_reserved_mb"] = torch.cuda.memory_reserved(device_index) / (1024 ** 2)
            metrics["gpu_peak_mb"] = torch.cuda.max_memory_allocated(device_index) / (1024 ** 2)
        else:
            metrics["gpu_used_mb"] = 0.0
            metrics["gpu_reserved_mb"] = 0.0
            metrics["gpu_peak_mb"] = 0.0
        return metrics

    def _worker_loop(self):
        while not self._stop_event.is_set():
            try:
                first_request = self.request_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            batch = [first_request]
            deadline = time.perf_counter() + (self.batch_wait_ms / 1000.0)
            while len(batch) < self.max_batch_size:
                timeout = deadline - time.perf_counter()
                if timeout <= 0:
                    break
                try:
                    batch.append(self.request_queue.get(timeout=timeout))
                except queue.Empty:
                    break

            self._process_batch(batch)

    def _process_batch(self, batch: List[FrameRequest]):
        detector_inputs = []
        detector_meta = []

        for request in batch:
            state = self.sessions.setdefault(request.session_id, SessionState())
            state.frame_index += 1

            short_circuit = self._precheck_request(state, request)
            if short_circuit is not None:
                self.metrics["returned_without_gpu"] += 1
                request.response_queue.put(short_circuit)
                continue

            detector_inputs.append(request.frame_bgr)
            detector_meta.append((request, state))

        if not detector_inputs:
            return

        self.metrics["gpu_batches"] += 1
        self.metrics["gpu_batch_items"] += len(detector_inputs)
        self.metrics["detector_frames"] += len(detector_inputs)

        results = self.detector.predict(
            detector_inputs,
            conf=self.threshold,
            device=self.detector_device,
            imgsz=self.detector_imgsz,
            max_det=self.max_detections,
            verbose=False,
            half=self.use_half,
            stream=False,
        )

        for result, (request, state) in zip(results, detector_meta):
            response = self._postprocess_detection(request, state, result)
            request.response_queue.put(response)

    def _precheck_request(self, state: SessionState, request: FrameRequest) -> Optional[Dict]:
        if request.force_process:
            state.last_thumb = self._make_thumb(request.frame_bgr)
            return None

        has_cached_result = bool(state.last_raw_text)
        thumb = self._make_thumb(request.frame_bgr)
        if state.last_thumb is not None:
            diff = float(np.mean(cv2.absdiff(thumb, state.last_thumb)))
            if has_cached_result and diff < self.thumb_diff_threshold:
                state.last_thumb = thumb
                return self._build_response(state, request, processed=False, reason="duplicate_frame")
        state.last_thumb = thumb

        return None

    def _postprocess_detection(self, request: FrameRequest, state: SessionState, result) -> Dict:
        frame = request.frame_bgr
        height, width = frame.shape[:2]
        best_bbox = None
        best_conf = 0.0
        best_score = -1.0

        for i in range(len(result.boxes.xyxy)):
            bbox = clamp_bbox(result.boxes.xyxy[i].tolist(), width, height)
            x1, y1, x2, y2 = bbox
            area = (x2 - x1) * (y2 - y1)
            det_conf = float(result.boxes.conf[i])
            score = area * det_conf
            if area < self.min_box_area:
                continue
            if score > best_score:
                best_score = score
                best_bbox = bbox
                best_conf = det_conf

        if best_bbox is None:
            state.last_bbox = None
            self._clear_text_state(state)
            return self._build_response(state, request, processed=True, reason="no_plate")

        state.last_bbox = best_bbox
        if state.last_raw_text and state.frame_index - state.last_ocr_frame < self.ocr_interval:
            return self._build_response(state, request, processed=True, reason="ocr_reused", det_conf=best_conf)

        x1, y1, x2, y2 = best_bbox
        plate_crop = frame[y1:y2, x1:x2]
        if plate_crop.size == 0:
            state.last_bbox = None
            self._clear_text_state(state)
            return self._build_response(state, request, processed=True, reason="empty_crop")

        plate_image = cv2.resize(plate_crop, (self.args.imgW, self.args.imgH), interpolation=cv2.INTER_AREA)
        plate_image = cv2.cvtColor(plate_image, cv2.COLOR_BGR2GRAY)
        ocr_text, confidence = self.recognizer.predict(plate_image, self.args)
        raw_text, persian_text = postprocess_plate_text(ocr_text)
        self.metrics["ocr_runs"] += 1
        state.last_ocr_frame = state.frame_index

        if raw_text:
            state.last_raw_text = raw_text
            state.last_persian_text = persian_text
            state.last_confidence = confidence
            state.votes[raw_text] += 1
            if state.votes[raw_text] >= self.stable_hits:
                state.stable_text = raw_text
                state.stable_persian_text = state.last_persian_text
        else:
            self._clear_text_state(state)

        return self._build_response(state, request, processed=True, reason="ocr_ran", det_conf=best_conf)

    @staticmethod
    def _clear_text_state(state: SessionState) -> None:
        state.last_raw_text = ""
        state.last_persian_text = ""
        state.last_confidence = 0.0
        state.votes.clear()
        state.stable_text = ""
        state.stable_persian_text = ""

    def _build_response(self, state: SessionState, request: FrameRequest, processed: bool, reason: str, det_conf: float = 0.0) -> Dict:
        latency_ms = (time.perf_counter() - request.enqueue_time) * 1000.0
        return {
            "accepted": True,
            "processed": processed,
            "reason": reason,
            "frame_index": state.frame_index,
            "bbox": state.last_bbox,
            "text": state.stable_text or state.last_raw_text,
            "persian_text": state.stable_persian_text or state.last_persian_text,
            "confidence": state.last_confidence,
            "detector_confidence": det_conf,
            "stable": bool(state.stable_text),
            "latency_ms": latency_ms,
            "queue_depth": self.request_queue.qsize(),
        }

    @staticmethod
    def _make_thumb(frame_bgr: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        return cv2.resize(gray, (16, 16), interpolation=cv2.INTER_AREA)
