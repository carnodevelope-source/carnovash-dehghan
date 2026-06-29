import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont

import arabic_reshaper
from bidi.algorithm import get_display


DEFAULT_OCR_CHARACTER_SET = "0123456789abcdefghijklmnopqrstuvwxyz"
PLATE_LENGTH = 8
PLATE_LETTER_INDEX = 2
PERSIAN_DIGIT_TABLE = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
PERSIAN_TO_LATIN_DIGIT_TABLE = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
DEFAULT_PLATE_FONT = Path(__file__).resolve().parent / "font" / "ttf" / "Vazirmatn-Regular.ttf"
PERSIAN_TO_LATIN_TOKENS = {
    "الف": "a",
    "ب": "b",
    "پ": "p",
    "ج": "j",
    "ح": "h",
    "د": "d",
    "ر": "r",
    "ز": "z",
    "س": "s",
    "ش": "x",
    "ص": "c",
    "ط": "t",
    "ع": "u",
    "ف": "f",
    "ق": "q",
    "ک": "k",
    "ك": "k",
    "گ": "g",
    "ل": "l",
    "م": "m",
    "ن": "n",
    "ه": "e",
    "و": "o",
    "ی": "i",
    "ي": "i",
}
LETTER_MAP = {
    "a": "الف",
    "b": "ب",
    "c": "ص",
    "d": "د",
    "e": "ه",
    "f": "ف",
    "g": "گ",
    "h": "ح",
    "i": "ی",
    "j": "ج",
    "k": "ک",
    "l": "ل",
    "m": "م",
    "n": "ن",
    "o": "و",
    "p": "پ",
    "q": "ق",
    "r": "ر",
    "s": "س",
    "t": "ط",
    "u": "ع",
    "v": "و",
    "w": "و",
    "x": "ش",
    "y": "ی",
    "z": "ز",
}
DIGIT_ALIASES = {
    "o": "0",
    "q": "0",
    "d": "0",
    "u": "0",
    "i": "1",
    "l": "1",
    "z": "2",
    "s": "5",
    "g": "6",
    "t": "7",
    "b": "8",
}
LETTER_ALIASES = {
    "0": "o",
    "1": "i",
    "2": "z",
    "5": "s",
    "6": "g",
    "7": "t",
    "8": "b",
}


def configure_torch_runtime(device: str, cpu_threads: int) -> None:
    if device in {"cuda", "auto"} and not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for this configuration, but no GPU is available.")
    if device == "cuda":
        return
    torch.set_num_threads(max(1, cpu_threads))
    if hasattr(torch, "set_num_interop_threads"):
        try:
            torch.set_num_interop_threads(1)
        except RuntimeError:
            pass


def _normalize_raw_plate_text(raw: str) -> str:
    normalized = raw.strip().lower().translate(PERSIAN_TO_LATIN_DIGIT_TABLE)
    for token, replacement in PERSIAN_TO_LATIN_TOKENS.items():
        normalized = normalized.replace(token, replacement)
    return "".join(ch for ch in normalized if ch.isascii() and ch.isalnum())


def _canonicalize_digit(ch: str) -> Tuple[str, int]:
    if ch.isdigit():
        return ch, 0
    if ch in DIGIT_ALIASES:
        return DIGIT_ALIASES[ch], 1
    return ch, 4


def _canonicalize_letter(ch: str) -> Tuple[str, int]:
    if ch in LETTER_MAP:
        return ch, 0
    if ch in LETTER_ALIASES:
        letter = LETTER_ALIASES[ch]
        if letter in LETTER_MAP:
            return letter, 1
    return ch, 4


def _canonicalize_plate_window(window: str) -> Tuple[str, int]:
    converted = []
    score = 0
    for index, ch in enumerate(window):
        if index == PLATE_LETTER_INDEX:
            mapped, penalty = _canonicalize_letter(ch)
        else:
            mapped, penalty = _canonicalize_digit(ch)
        converted.append(mapped)
        score += penalty
    return "".join(converted), score


def canonicalize_plate_text(raw: str) -> str:
    cleaned = _normalize_raw_plate_text(raw)
    if not cleaned:
        return ""

    if len(cleaned) >= PLATE_LENGTH:
        best_text = ""
        best_score = None
        for start in range(len(cleaned) - PLATE_LENGTH + 1):
            candidate, score = _canonicalize_plate_window(cleaned[start:start + PLATE_LENGTH])
            if best_score is None or score < best_score:
                best_text = candidate
                best_score = score
        if best_text:
            return best_text

    converted = []
    for index, ch in enumerate(cleaned):
        if index == PLATE_LETTER_INDEX:
            mapped, _ = _canonicalize_letter(ch)
        else:
            mapped, _ = _canonicalize_digit(ch)
        converted.append(mapped)
    return "".join(converted)


def format_plate_persian(raw: str) -> str:
    canonical = canonicalize_plate_text(raw)
    if not canonical:
        return ""

    converted = []
    for ch in canonical:
        if ch.isdigit():
            converted.append(ch.translate(PERSIAN_DIGIT_TABLE))
        elif ch in LETTER_MAP:
            converted.append(LETTER_MAP[ch])
        else:
            converted.append(ch)

    if len(converted) == PLATE_LENGTH:
        return (
            f"{converted[0]}{converted[1]} "
            f"{converted[2]} "
            f"{converted[3]}{converted[4]}{converted[5]} "
            f"{converted[6]}{converted[7]}"
        )
    return " ".join(converted)


def postprocess_plate_text(raw: str) -> Tuple[str, str]:
    canonical = canonicalize_plate_text(raw)
    return canonical, format_plate_persian(canonical)


def normalize_plate(raw: str) -> str:
    return format_plate_persian(raw)


def make_rtl_text(text: str) -> str:
    try:
        return get_display(arabic_reshaper.reshape(text))
    except Exception:
        return text


def resolve_plate_font(font_path: str = "") -> str:
    if font_path and os.path.exists(font_path):
        return font_path
    if DEFAULT_PLATE_FONT.exists():
        return str(DEFAULT_PLATE_FONT)
    return ""


def draw_text_box_pil(
    frame,
    text: str,
    position: Tuple[int, int],
    font_path: str = "",
    font_size: int = 32,
    text_color: Tuple[int, int, int] = (255, 255, 0),
    box_color: Tuple[int, int, int] = (0, 0, 0),
):
    image_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(image_pil)
    resolved_font_path = resolve_plate_font(font_path)
    font = ImageFont.truetype(resolved_font_path, font_size) if resolved_font_path else ImageFont.load_default()
    x, y = position
    text_to_draw = make_rtl_text(text)

    try:
        bbox = draw.textbbox((x, y), text_to_draw, font=font)
        draw.rectangle((bbox[0] - 8, bbox[1] - 6, bbox[2] + 8, bbox[3] + 6), fill=box_color)
    except Exception:
        pass

    draw.text((x, y), text_to_draw, font=font, fill=text_color)
    return cv2.cvtColor(np.array(image_pil), cv2.COLOR_RGB2BGR)


def clamp_bbox(bbox, width: int, height: int) -> Tuple[int, int, int, int]:
    x1, y1, x2, y2 = map(int, bbox)
    return max(0, x1), max(0, y1), min(width, x2), min(height, y2)


def bbox_iou(box_a: Tuple[int, int, int, int], box_b: Tuple[int, int, int, int]) -> float:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    inter_w = max(0, inter_x2 - inter_x1)
    inter_h = max(0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h
    if inter_area == 0:
        return 0.0

    area_a = max(0, ax2 - ax1) * max(0, ay2 - ay1)
    area_b = max(0, bx2 - bx1) * max(0, by2 - by1)
    denom = area_a + area_b - inter_area
    return inter_area / denom if denom else 0.0


def reuse_cached_text(
    cache: List[Dict],
    bbox: Tuple[int, int, int, int],
    frame_index: int,
    max_age: int,
    min_iou: float,
) -> Optional[Dict]:
    best_match = None
    best_iou = 0.0
    for item in cache:
        age = frame_index - item["frame_index"]
        if age > max_age:
            continue
        overlap = bbox_iou(bbox, item["bbox"])
        if overlap >= min_iou and overlap > best_iou:
            best_iou = overlap
            best_match = item
    return best_match
