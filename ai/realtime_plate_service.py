import argparse
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

import cv2
import numpy as np
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
    stable_text: str = ""
    stable_persian_text: str = ""
    votes: Counter = field(default_factory=Counter)


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
    args.device = "cuda"
    args.half = True
    return args


class RealtimePlateService:
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
    ):
        self.args = build_runtime_args()
        configure_torch_runtime("cuda", 1)
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
        self.sessions: Dict[str, SessionState] = {}

    def get_session(self, session_id: str) -> SessionState:
        state = self.sessions.get(session_id)
        if state is None:
            state = SessionState()
            self.sessions[session_id] = state
        return state

    def drop_session(self, session_id: str) -> None:
        self.sessions.pop(session_id, None)

    def process_frame(self, session_id: str, frame_bgr: np.ndarray) -> Dict:
        state = self.get_session(session_id)
        state.frame_index += 1

        thumb = self._make_thumb(frame_bgr)
        if state.last_thumb is not None:
            diff = float(np.mean(cv2.absdiff(thumb, state.last_thumb)))
            if diff < self.thumb_diff_threshold:
                state.last_thumb = thumb
                return self._build_response(state, processed=False, reason="duplicate_frame")
        state.last_thumb = thumb

        if state.frame_index % self.keyframe_interval != 0:
            return self._build_response(state, processed=False, reason="non_keyframe")

        best_detection = self._detect_best_plate(frame_bgr)
        if best_detection is None:
            return self._build_response(state, processed=True, reason="no_plate")

        bbox, det_conf = best_detection
        state.last_bbox = bbox

        if state.last_raw_text and state.frame_index - state.last_ocr_frame < self.ocr_interval:
            return self._build_response(state, processed=True, reason="ocr_reused", det_conf=det_conf)

        x1, y1, x2, y2 = bbox
        plate_crop = frame_bgr[y1:y2, x1:x2]
        if plate_crop.size == 0:
            return self._build_response(state, processed=True, reason="empty_crop")

        plate_image = cv2.resize(plate_crop, (self.args.imgW, self.args.imgH), interpolation=cv2.INTER_AREA)
        plate_image = cv2.cvtColor(plate_image, cv2.COLOR_BGR2GRAY)
        ocr_text, confidence = self.recognizer.predict(plate_image, self.args)
        raw_text, persian_text = postprocess_plate_text(ocr_text)
        state.last_ocr_frame = state.frame_index

        if raw_text:
            state.last_raw_text = raw_text
            state.last_persian_text = persian_text
            state.last_confidence = confidence
            state.votes[raw_text] += 1
            if state.votes[raw_text] >= self.stable_hits:
                state.stable_text = raw_text
                state.stable_persian_text = state.last_persian_text

        return self._build_response(state, processed=True, reason="ocr_ran", det_conf=det_conf)

    def _detect_best_plate(self, frame_bgr: np.ndarray) -> Optional[Tuple[Tuple[int, int, int, int], float]]:
        height, width = frame_bgr.shape[:2]
        results = self.detector.predict(
            frame_bgr,
            conf=self.threshold,
            device="cuda",
            imgsz=self.detector_imgsz,
            max_det=self.max_detections,
            verbose=False,
            half=True,
        )

        best_bbox = None
        best_score = -1.0
        for result in results:
            for i in range(len(result.boxes.xyxy)):
                bbox = clamp_bbox(result.boxes.xyxy[i].tolist(), width, height)
                x1, y1, x2, y2 = bbox
                area = (x2 - x1) * (y2 - y1)
                det_conf = float(result.boxes.conf[i])
                score = det_conf * area
                if area < self.min_box_area:
                    continue
                if score > best_score:
                    best_score = score
                    best_bbox = (bbox, det_conf)
        return best_bbox

    def _make_thumb(self, frame_bgr: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        return cv2.resize(gray, (16, 16), interpolation=cv2.INTER_AREA)

    def _build_response(self, state: SessionState, processed: bool, reason: str, det_conf: float = 0.0) -> Dict:
        return {
            "processed": processed,
            "reason": reason,
            "frame_index": state.frame_index,
            "bbox": state.last_bbox,
            "text": state.stable_text or state.last_raw_text,
            "persian_text": state.stable_persian_text or state.last_persian_text,
            "confidence": state.last_confidence,
            "detector_confidence": det_conf,
            "stable": bool(state.stable_text),
        }
