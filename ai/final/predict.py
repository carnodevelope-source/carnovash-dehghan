"""Standalone final inference: one image -> {'plate': str, 'color': str}."""

from __future__ import annotations

import argparse
import os
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import cv2
import numpy as np
import torch
from PIL import Image
from ultralytics import YOLO


ROOT = Path(__file__).resolve().parent
WEIGHTS = ROOT / "weights"
_REQUESTED_DEVICE = os.getenv("PLATE_AI_DEVICE", "auto").strip().lower()
DEVICE = ("cuda" if torch.cuda.is_available() else "cpu") if _REQUESTED_DEVICE == "auto" else _REQUESTED_DEVICE
if DEVICE == "cuda" and not torch.cuda.is_available():
    raise RuntimeError("PLATE_AI_DEVICE=cuda was requested but CUDA is not available.")
OCR_CHARS = ["[GO]", "[s]", *list("0123456789abcdefghijklmnopqrstuvwxyz")]
LETTER_LABELS = ["a", "b", "c", "d", "e", "j", "l", "m", "n", "o", "q", "s", "t"]
COLOR_LABELS = ["دلفینی", "سفید", "مشکی", "نقره‌ای", "نوک‌مدادی"]
LETTER_THRESHOLD = 0.7015
PLATE_THRESHOLD = 0.52
MEAN = np.asarray((0.485, 0.456, 0.406), dtype=np.float32).reshape(1, 1, 3)
STD = np.asarray((0.229, 0.224, 0.225), dtype=np.float32).reshape(1, 1, 3)
LETTER_MAP = {
    "a": "الف", "b": "ب", "c": "ص", "d": "د", "e": "ه", "j": "ج", "l": "ل",
    "m": "م", "n": "ن", "o": "و", "q": "ق", "s": "س", "t": "ط", "h": "ح",
    "i": "ی", "p": "پ", "r": "ر", "x": "ش", "z": "ز", "f": "ف", "g": "گ",
    "k": "ک", "u": "ع", "v": "و", "w": "و", "y": "ی",
}
DIGIT_ALIASES = {"o": "0", "q": "0", "d": "0", "u": "0", "i": "1", "l": "1", "z": "2", "s": "5", "g": "6", "t": "7", "b": "8"}
LETTER_ALIASES = {"0": "o", "1": "i", "2": "z", "5": "s", "6": "g", "7": "t", "8": "b"}


class _Models:
    def __init__(self) -> None:
        required = ("plate_detector.pt", "vehicle_detector.pt", "ocr_model.ts", "letter_model.ts", "color_model.ts")
        missing = [name for name in required if not (WEIGHTS / name).is_file()]
        if missing:
            raise FileNotFoundError("Missing weight(s): " + ", ".join(missing))
        self.plate_detector = YOLO(str(WEIGHTS / "plate_detector.pt"))
        self.vehicle_detector = YOLO(str(WEIGHTS / "vehicle_detector.pt"))
        ocr_weight = WEIGHTS / "ocr_model_cuda.ts" if DEVICE == "cuda" and (WEIGHTS / "ocr_model_cuda.ts").exists() else WEIGHTS / "ocr_model.ts"
        self.ocr_device = DEVICE if ocr_weight.name.endswith("_cuda.ts") else "cpu"
        self.ocr = torch.jit.load(str(ocr_weight), map_location=self.ocr_device).eval()
        self.letter = torch.jit.load(str(WEIGHTS / "letter_model.ts"), map_location=DEVICE).eval()
        self.color = torch.jit.load(str(WEIGHTS / "color_model.ts"), map_location=DEVICE).eval()


_MODELS: _Models | None = None


def _models() -> _Models:
    global _MODELS
    if _MODELS is None:
        _MODELS = _Models()
    return _MODELS


def _imagenet_tensor(image_bgr: np.ndarray, size: int, grayscale: bool = False) -> torch.Tensor:
    if grayscale:
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        image_rgb = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
    else:
        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    # Match torchvision's PIL Resize + ToTensor used during training.
    image = np.asarray(Image.fromarray(image_rgb).resize((size, size), Image.Resampling.BILINEAR), dtype=np.float32)
    normalized = (image.astype(np.float32) / 255.0 - MEAN) / STD
    return torch.from_numpy(normalized.transpose(2, 0, 1)).unsqueeze(0).to(DEVICE)


def _canonical(raw: str) -> str:
    cleaned = "".join(ch for ch in raw.lower() if ch.isascii() and ch.isalnum())
    if len(cleaned) < 8:
        return ""
    best = None
    for start in range(len(cleaned) - 7):
        candidate = cleaned[start:start + 8]; converted = []; penalty = 0
        for index, ch in enumerate(candidate):
            if index == 2:
                if ch in LETTER_MAP: converted.append(ch)
                elif ch in LETTER_ALIASES: converted.append(LETTER_ALIASES[ch]); penalty += 1
                else: converted.append(ch); penalty += 5
            else:
                if ch.isdigit(): converted.append(ch)
                elif ch in DIGIT_ALIASES: converted.append(DIGIT_ALIASES[ch]); penalty += 1
                else: converted.append(ch); penalty += 5
        value = "".join(converted)
        if best is None or penalty < best[0]: best = (penalty, value)
    return best[1] if best and best[0] < 5 else ""


def _persian(label: str) -> str:
    if len(label) != 8 or label[2] not in LETTER_MAP:
        return "unknown"
    digits = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
    return f"{label[6:8].translate(digits)} {LETTER_MAP[label[2]]} {label[3:6].translate(digits)} {label[:2].translate(digits)}"


def _expand(box, width: int, height: int, margin: float) -> Tuple[int, int, int, int]:
    x1, y1, x2, y2 = map(float, box); dx = (x2 - x1) * margin; dy = (y2 - y1) * margin
    return max(0, int(round(x1 - dx))), max(0, int(round(y1 - dy))), min(width, int(round(x2 + dx))), min(height, int(round(y2 + dy)))


def _order_points(points: np.ndarray) -> np.ndarray:
    ordered = np.zeros((4, 2), dtype=np.float32); sums = points.sum(axis=1); diffs = np.diff(points, axis=1).reshape(-1)
    ordered[0], ordered[2] = points[np.argmin(sums)], points[np.argmax(sums)]
    ordered[1], ordered[3] = points[np.argmin(diffs)], points[np.argmax(diffs)]
    return ordered


def _rectify_plate(crop: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY); edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 55, 160)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE); crop_area = crop.shape[0] * crop.shape[1]
    for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:12]:
        polygon = cv2.approxPolyDP(contour, 0.025 * cv2.arcLength(contour, True), True)
        if len(polygon) != 4 or cv2.contourArea(polygon) < crop_area * 0.38: continue
        tl, tr, br, bl = _order_points(polygon.reshape(4, 2).astype(np.float32))
        target_w = int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl))); target_h = int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl)))
        if target_w < 50 or target_h < 15 or target_w / max(1, target_h) < 2.0: continue
        destination = np.array([[0, 0], [target_w - 1, 0], [target_w - 1, target_h - 1], [0, target_h - 1]], dtype=np.float32)
        return cv2.warpPerspective(crop, cv2.getPerspectiveTransform(np.array([tl, tr, br, bl]), destination), (target_w, target_h), flags=cv2.INTER_CUBIC)
    return crop


def _plate_crop(image: np.ndarray) -> np.ndarray | None:
    result = _models().plate_detector.predict(image, conf=0.30, imgsz=640, device=DEVICE, max_det=4, verbose=False)[0]
    if result.boxes is None or len(result.boxes) == 0: return None
    height, width = image.shape[:2]; best = None
    for index in range(len(result.boxes)):
        box = _expand(result.boxes.xyxy[index].tolist(), width, height, 0.08)
        x1, y1, x2, y2 = box; area = max(0, x2 - x1) * max(0, y2 - y1)
        confidence = float(result.boxes.conf[index]); score = confidence * np.sqrt(max(1, area))
        if area >= 300 and (best is None or score > best[0]): best = (score, box)
    if best is None: return None
    x1, y1, x2, y2 = best[1]
    return _rectify_plate(image[y1:y2, x1:x2])


def _vehicle_crop(image: np.ndarray) -> np.ndarray:
    result = _models().vehicle_detector.predict(image, conf=0.22, imgsz=640, device=DEVICE, max_det=8, classes=[2, 3, 5, 7], verbose=False)[0]
    height, width = image.shape[:2]; best = None
    if result.boxes is not None:
        for index in range(len(result.boxes)):
            box = _expand(result.boxes.xyxy[index].tolist(), width, height, 0.06)
            x1, y1, x2, y2 = box; area = max(1, (x2 - x1) * (y2 - y1)); confidence = float(result.boxes.conf[index])
            score = confidence * np.sqrt(area)
            if best is None or score > best[0]: best = (score, box)
    if best is not None:
        x1, y1, x2, y2 = best[1]; return image[y1:y2, x1:x2]
    return image[int(height * .03):int(height * .97), int(width * .04):int(width * .96)]


def _ocr_one(gray: np.ndarray) -> Tuple[str, float]:
    resized = cv2.resize(gray, (100, 32), interpolation=cv2.INTER_CUBIC)
    ocr_device = _models().ocr_device
    tensor = torch.from_numpy(resized.astype(np.float32) / 127.5 - 1.0).unsqueeze(0).unsqueeze(0).to(ocr_device)
    text = torch.zeros(1, 26, dtype=torch.long, device=ocr_device)
    with torch.inference_mode(): logits = _models().ocr(tensor, text)
    probabilities = logits.softmax(2); confidence_values, indices = probabilities.max(2)
    chars = []; probs = []
    for index, confidence in zip(indices[0].tolist(), confidence_values[0].tolist()):
        char = OCR_CHARS[index]
        if char == "[s]": break
        if char != "[GO]": chars.append(char); probs.append(confidence)
    confidence = float(np.prod(probs)) if probs else 0.0
    return "".join(chars), confidence


def _ocr_batch(views: List[np.ndarray]) -> List[Tuple[str, float]]:
    """Run all plate enhancement views in one GPU pass."""
    arrays = [cv2.resize(view, (100, 32), interpolation=cv2.INTER_CUBIC).astype(np.float32) / 127.5 - 1.0 for view in views]
    ocr_device = _models().ocr_device
    tensor = torch.from_numpy(np.stack(arrays)).unsqueeze(1).to(ocr_device)
    text = torch.zeros(len(views), 26, dtype=torch.long, device=ocr_device)
    with torch.inference_mode(): logits = _models().ocr(tensor, text)
    probabilities = logits.softmax(2); confidence_values, indices = probabilities.max(2)
    output = []
    for row_indices, row_confidences in zip(indices.tolist(), confidence_values.tolist()):
        chars = []; probs = []
        for index, confidence in zip(row_indices, row_confidences):
            char = OCR_CHARS[index]
            if char == "[s]": break
            if char != "[GO]": chars.append(char); probs.append(confidence)
        output.append(("".join(chars), float(np.prod(probs)) if probs else 0.0))
    return output


def _read_plate_details(crop: np.ndarray | None) -> Dict[str, object]:
    empty = {"latin": "unknown", "persian": "unknown", "confidence": 0.0, "status": "unknown"}
    if crop is None or crop.size == 0: return empty
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(2.0, (8, 4)).apply(gray)
    sharpened = cv2.addWeighted(gray, 1.8, cv2.GaussianBlur(gray, (0, 0), 1.0), -0.8, 0)
    predictions = []; scores = defaultdict(float); maximum = defaultdict(float)
    for raw, confidence in _ocr_batch([gray, clahe, sharpened]):
        label = _canonical(raw); predictions.append(label)
        if len(label) == 8: scores[label] += max(0.02, confidence); maximum[label] = max(maximum[label], confidence)
    if not scores: return empty
    label = max(scores, key=scores.get); consensus = predictions.count(label) / 3.0
    confidence = min(1.0, 0.60 * maximum[label] + 0.40 * consensus)
    height, width = crop.shape[:2]; letter_roi = crop[int(height * .02):int(height * .98), int(width * .18):int(width * .43)]
    with torch.inference_mode(): letter_probs = _models().letter(_imagenet_tensor(letter_roi, 128, True)).softmax(1)[0]
    letter_conf, letter_index = letter_probs.max(0)
    if float(letter_conf) >= LETTER_THRESHOLD:
        label = label[:2] + LETTER_LABELS[int(letter_index)] + label[3:]
        confidence = min(confidence, 0.55 + 0.45 * float(letter_conf))
    if confidence < PLATE_THRESHOLD:
        return {**empty, "confidence": round(confidence, 4)}
    persian = _persian(label)
    if persian == "unknown":
        return {**empty, "confidence": round(confidence, 4)}
    return {"latin": label, "persian": persian, "confidence": round(confidence, 4), "status": "ok"}


def _read_plate(crop: np.ndarray | None) -> str:
    return str(_read_plate_details(crop)["persian"])


def _histogram(image: np.ndarray) -> torch.Tensor:
    height, width = image.shape[:2]; region = image[int(height * .12):int(height * .92), int(width * .08):int(width * .92)]
    hsv = cv2.cvtColor(region if region.size else image, cv2.COLOR_BGR2HSV)
    mask = (hsv[:, :, 2] > 18).astype(np.uint8) * 255
    if cv2.countNonZero(mask) < hsv.shape[0] * hsv.shape[1] * .20: mask = None
    values = []
    for channel, upper in ((0, 180), (1, 256), (2, 256)):
        hist = cv2.calcHist([hsv], [channel], mask, [16], [0, upper]).reshape(-1); hist /= max(1.0, float(hist.sum())); values.extend(hist)
    return torch.tensor(values, dtype=torch.float32, device=DEVICE).unsqueeze(0)


def _region_tone(region: np.ndarray) -> Dict[str, float] | None:
    if region is None or region.size == 0:
        return None
    hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV).astype(np.float32)
    value = hsv[:, :, 2]
    saturation = hsv[:, :, 1]
    # Ignore crushed blacks and blown headlights / specular spikes.
    mask = (value > 40) & (value < 235) & (saturation < 95)
    if int(mask.sum()) < 200:
        mask = (value > 30) & (value < 245)
    samples = value[mask]
    if samples.size < 100:
        return None
    return {
        "v_median": float(np.median(samples)),
        "bright_ratio": float((samples > 180).mean()),
        "mid_ratio": float(((samples > 80) & (samples < 170)).mean()),
        "dark_ratio": float((samples < 90).mean()),
    }


def _paint_tone(crop: np.ndarray) -> Dict[str, float]:
    """Body-paint brightness used to separate سفید / نقره‌ای / نوک‌مدادی."""
    height, width = crop.shape[:2]
    candidates = [
        _region_tone(crop[int(height * 0.18):int(height * 0.58), int(width * 0.18):int(width * 0.82)]),
        _region_tone(crop[int(height * 0.15):int(height * 0.70), int(width * 0.12):int(width * 0.88)]),
        _region_tone(crop[int(height * 0.30):int(height * 0.70), int(width * 0.10):int(width * 0.90)]),
    ]
    tones = [tone for tone in candidates if tone is not None]
    if not tones:
        return {"v_median": 0.0, "bright_ratio": 0.0, "mid_ratio": 0.0, "dark_ratio": 1.0}
    # Prefer painted mid-gray panels; avoid sun specular and crushed shadow patches.
    return max(
        tones,
        key=lambda tone: (
            tone["mid_ratio"] - 0.40 * tone["dark_ratio"] - 0.55 * tone["bright_ratio"],
            -abs(tone["v_median"] - 125.0),
        ),
    )


def _disambiguate_achromatic(probabilities: torch.Tensor, crop: np.ndarray) -> Tuple[int, float]:
    """Separate سفید / نقره‌ای / نوک‌مدادی using paint tone (day + night)."""
    white_i = COLOR_LABELS.index("سفید")
    silver_i = COLOR_LABELS.index("نقره‌ای")
    probs = probabilities.detach().float().cpu()
    index = int(torch.argmax(probs).item())
    confidence = float(probs[index].item())
    name = COLOR_LABELS[index]
    if name not in {"سفید", "نقره‌ای", "نوک‌مدادی"}:
        return index, confidence

    white_p = float(probs[white_i].item())
    silver_p = float(probs[silver_i].item())
    tone = _paint_tone(crop)
    looks_white = tone["v_median"] >= 155.0 or tone["bright_ratio"] >= 0.40
    clearly_white = tone["v_median"] >= 185.0 and tone["bright_ratio"] >= 0.55
    # Mid-gray body in day or night; allow some sun specular on metallic paint.
    looks_silver = (
        70.0 <= tone["v_median"] <= 152.0
        and tone["mid_ratio"] >= 0.35
        and tone["bright_ratio"] < 0.36
        and tone["dark_ratio"] < 0.55
        and not looks_white
    )
    # Lighter silver is often predicted as نوک‌مدادی under hard daylight.
    looks_light_silver = (
        tone["v_median"] >= 115.0
        and tone["mid_ratio"] >= 0.48
        and tone["bright_ratio"] < 0.35
        and tone["dark_ratio"] < 0.32
        and not looks_white
    )

    # Trust a confident silver prediction unless the body is clearly blown white.
    if name == "نقره‌ای" and confidence >= 0.55 and not clearly_white:
        return index, confidence
    if looks_white and not looks_silver:
        return white_i, min(0.95, max(confidence, white_p, 0.42) + 0.08)
    if name == "نوک‌مدادی" and looks_light_silver:
        return silver_i, min(0.95, max(0.50, silver_p + 0.22))
    if looks_silver:
        boosted = max(silver_p, 0.42 if name in {"سفید", "نوک‌مدادی"} else confidence)
        return silver_i, min(0.95, boosted + 0.12)
    if name == "نقره‌ای" and clearly_white:
        return white_i, min(0.95, max(0.45, white_p + 0.08))
    return index, confidence


def _read_color_details(crop: np.ndarray) -> Dict[str, object]:
    with torch.inference_mode(): probabilities = _models().color(_imagenet_tensor(crop, 224), _histogram(crop)).softmax(1)[0]
    index, confidence_value = _disambiguate_achromatic(probabilities, crop)
    return {
        "name": COLOR_LABELS[index],
        "confidence": round(confidence_value, 4),
        "reliable": confidence_value >= 0.35,
    }


def _read_color(crop: np.ndarray) -> str:
    return str(_read_color_details(crop)["name"])


def predict(image_path: str | Path) -> Dict[str, str]:
    """Public API. Models are cached after the first call."""
    image = cv2.imread(str(Path(image_path).expanduser().resolve()))
    if image is None: raise ValueError(f"Cannot read image: {image_path}")
    return {"plate": _read_plate(_plate_crop(image)), "color": _read_color(_vehicle_crop(image))}


def main() -> None:
    parser = argparse.ArgumentParser(description="One image -> Persian plate and color")
    parser.add_argument("image", help="input image path")
    args = parser.parse_args(); print(predict(args.image))


if __name__ == "__main__": main()
