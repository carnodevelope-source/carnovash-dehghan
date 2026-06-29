import argparse
import contextlib
import io
import os
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple

import cv2
import torch
from ultralytics import YOLO

from deep_text_recognition_benchmark.dtrb import DTRB
from light_plate_common import DEFAULT_OCR_CHARACTER_SET, postprocess_plate_text


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


def latin_to_persian_digits(text: str) -> str:
    return text.translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def normalize_plate(raw: str) -> str:
    return postprocess_plate_text(raw)[1]


def parse_dtrb_output(output: str) -> Tuple[str, str]:
    lines = [line.strip() for line in output.splitlines() if line.strip()]

    for line in reversed(lines):
        parts = line.split()
        if len(parts) >= 3:
            label = parts[-2]
            conf = parts[-1]
            if re.match(r"^[0-9a-zA-Z]+$", label):
                return label, conf

    return "", ""


def predict_plate_text(plate_recognizer, plate_image_gray, opt) -> Tuple[str, float]:
    ocr_text, confidence = plate_recognizer.predict(plate_image_gray, opt)
    return postprocess_plate_text(ocr_text)[0], confidence


def get_gpu_stats():
    if not torch.cuda.is_available():
        return {
            "available": False,
            "used_mb": 0.0,
            "reserved_mb": 0.0,
            "peak_mb": 0.0,
            "total_mb": 0.0,
        }

    device_index = torch.cuda.current_device()
    props = torch.cuda.get_device_properties(device_index)

    return {
        "available": True,
        "used_mb": torch.cuda.memory_allocated(device_index) / (1024 ** 2),
        "reserved_mb": torch.cuda.memory_reserved(device_index) / (1024 ** 2),
        "peak_mb": torch.cuda.max_memory_allocated(device_index) / (1024 ** 2),
        "total_mb": props.total_memory / (1024 ** 2),
    }


@dataclass
class StreamState:
    stream_id: int
    input_video: str
    cap: cv2.VideoCapture
    frame_index: int = 0
    frames_read: int = 0
    frames_processed: int = 0
    detections_seen: int = 0
    plate_counts: Counter = field(default_factory=Counter)
    matched_plate: str = ""
    matched_persian: str = ""
    status: str = "running"
    stop_reason: str = ""


def open_stream(stream_id: int, input_video: str) -> StreamState:
    cap = cv2.VideoCapture(input_video)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {input_video}")
    return StreamState(stream_id=stream_id, input_video=input_video, cap=cap)


def close_stream(stream: StreamState) -> None:
    if stream.cap is not None:
        stream.cap.release()


def expand_inputs(input_videos: List[str], input_list: str, repeat_inputs: int) -> List[str]:
    videos = []

    for item in input_videos:
        if item:
            videos.append(item)

    if input_list:
        with open(input_list, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    videos.append(line)

    if not videos:
        raise ValueError("No videos provided. Use --input-videos or --input-list.")

    expanded = videos * max(1, repeat_inputs)
    return [str(Path(video)) for video in expanded]


def run_session(concurrency: int, video_paths: List[str], detector, recognizer, opt):
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()

    streams = []
    session_start = time.time()
    peak_used_mb = 0.0
    peak_reserved_mb = 0.0

    try:
        for stream_id in range(concurrency):
            streams.append(open_stream(stream_id + 1, video_paths[stream_id % len(video_paths)]))

        while True:
            active_streams = [stream for stream in streams if stream.status == "running"]
            if not active_streams:
                break

            frames = []
            frame_streams = []

            for stream in active_streams:
                ret, frame = stream.cap.read()
                if not ret:
                    stream.status = "completed_without_match"
                    stream.stop_reason = "video_ended"
                    continue

                stream.frames_read += 1
                should_process = stream.frame_index % opt.process_every == 0
                stream.frame_index += 1

                if should_process:
                    stream.frames_processed += 1
                    frames.append(frame)
                    frame_streams.append((stream, frame))

            if not frames:
                continue

            try:
                results = detector.predict(frames, verbose=False, stream=False)
            except RuntimeError as exc:
                if "out of memory" in str(exc).lower():
                    raise
                raise

            for result, (stream, frame) in zip(results, frame_streams):
                height, width = frame.shape[:2]
                matched = False

                for i in range(len(result.boxes.xyxy)):
                    det_conf = float(result.boxes.conf[i])
                    if det_conf < opt.threshold:
                        continue

                    bbox = result.boxes.xyxy[i].cpu().detach().numpy().astype(int)
                    x1, y1, x2, y2 = bbox
                    x1 = max(0, x1)
                    y1 = max(0, y1)
                    x2 = min(width - 1, x2)
                    y2 = min(height - 1, y2)

                    plate_crop = frame[y1:y2, x1:x2].copy()
                    if plate_crop.size == 0:
                        continue

                    plate_image = cv2.resize(plate_crop, (100, 32))
                    plate_image = cv2.cvtColor(plate_image, cv2.COLOR_BGR2GRAY)

                    raw_text, _ = predict_plate_text(recognizer, plate_image, opt)
                    if not raw_text:
                        continue

                    stream.detections_seen += 1
                    stream.plate_counts[raw_text] += 1

                    if stream.plate_counts[raw_text] >= opt.success_count:
                        stream.status = "success"
                        stream.stop_reason = f"matched_{opt.success_count}_times"
                        stream.matched_plate = raw_text
                        stream.matched_persian = normalize_plate(raw_text)
                        matched = True
                        break

                if matched:
                    close_stream(stream)

            stats = get_gpu_stats()
            peak_used_mb = max(peak_used_mb, stats["used_mb"], stats["peak_mb"])
            peak_reserved_mb = max(peak_reserved_mb, stats["reserved_mb"])

            if opt.gpu_report_every > 0:
                total_processed = sum(stream.frames_processed for stream in streams)
                if total_processed % opt.gpu_report_every == 0:
                    print(
                        f"[concurrency {concurrency}] processed={total_processed} "
                        f"gpu_used={stats['used_mb']:.0f}MB reserved={stats['reserved_mb']:.0f}MB"
                    )

        elapsed_sec = time.time() - session_start
        completed = [stream for stream in streams if stream.status == "success"]
        unfinished = [stream for stream in streams if stream.status != "success"]

        for stream in unfinished:
            if stream.status == "running":
                stream.status = "completed_without_match"
                stream.stop_reason = "video_ended_or_not_enough_matches"
            close_stream(stream)

        return {
            "concurrency": concurrency,
            "status": "success",
            "elapsed_sec": elapsed_sec,
            "peak_used_mb": peak_used_mb,
            "peak_reserved_mb": peak_reserved_mb,
            "successful_streams": len(completed),
            "total_streams": len(streams),
            "streams": streams,
        }

    finally:
        for stream in streams:
            close_stream(stream)


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--batch_size", type=int, default=192)
    parser.add_argument("--batch_max_length", type=int, default=25)
    parser.add_argument("--imgH", type=int, default=32)
    parser.add_argument("--imgW", type=int, default=100)
    parser.add_argument("--rgb", action="store_true")
    parser.add_argument("--character", type=str, default=DEFAULT_OCR_CHARACTER_SET)
    parser.add_argument("--sensitive", action="store_true")
    parser.add_argument("--PAD", action="store_true")
    parser.add_argument("--Transformation", type=str, default="TPS")
    parser.add_argument("--FeatureExtraction", type=str, default="ResNet")
    parser.add_argument("--SequenceModeling", type=str, default="BiLSTM")
    parser.add_argument("--Prediction", type=str, default="Attn")
    parser.add_argument("--num_fiducial", type=int, default=20)
    parser.add_argument("--input_channel", type=int, default=1)
    parser.add_argument("--output_channel", type=int, default=512)
    parser.add_argument("--hidden_size", type=int, default=256)

    parser.add_argument(
        "--detector-weights",
        type=str,
        default="weigths/yolov8-detector/yolov8-s-license-plate-detector.pt",
    )
    parser.add_argument(
        "--recognizer-weights",
        type=str,
        default="weigths/dtrb-recoginzer/dtrb-None-VGG-BiLSTM-CTC-license-plate-recognizer.pth",
    )

    parser.add_argument("--input-videos", nargs="*", default=[])
    parser.add_argument("--input-list", type=str, default="")
    parser.add_argument("--repeat-inputs", type=int, default=20)
    parser.add_argument("--start-concurrency", type=int, default=1)
    parser.add_argument("--max-concurrency", type=int, default=10)
    parser.add_argument("--step", type=int, default=1)
    parser.add_argument("--success-count", type=int, default=3)
    parser.add_argument("--threshold", type=float, default=0.6)
    parser.add_argument("--process-every", type=int, default=1)
    parser.add_argument("--gpu-report-every", type=int, default=10)

    return parser.parse_args()


def main():
    opt = parse_args()
    video_paths = expand_inputs(opt.input_videos, opt.input_list, opt.repeat_inputs)

    print("loading detector once ...")
    detector = YOLO(opt.detector_weights)
    print("loading recognizer once ...")
    recognizer = DTRB(opt.recognizer_weights, opt)

    print(f"videos available for reuse: {len(video_paths)}")
    print(f"probe range: {opt.start_concurrency}..{opt.max_concurrency} step {opt.step}")

    results = []

    for concurrency in range(opt.start_concurrency, opt.max_concurrency + 1, opt.step):
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        print("")
        print(f"=== probing concurrency={concurrency} ===")

        try:
            result = run_session(concurrency, video_paths, detector, recognizer, opt)
            results.append(result)

            throughput = (
                result["successful_streams"] / result["elapsed_sec"]
                if result["elapsed_sec"] > 0
                else 0.0
            )

            print(
                f"success streams={result['successful_streams']}/{result['total_streams']} "
                f"time={result['elapsed_sec']:.2f}s "
                f"throughput={throughput:.2f} streams/s "
                f"peak_used={result['peak_used_mb']:.0f}MB "
                f"peak_reserved={result['peak_reserved_mb']:.0f}MB"
            )

        except RuntimeError as exc:
            if "out of memory" in str(exc).lower():
                print(f"OOM at concurrency={concurrency}")
                break
            raise

    if not results:
        print("no successful probe result")
        return

    best = max(
        results,
        key=lambda item: (
            item["successful_streams"] / item["elapsed_sec"] if item["elapsed_sec"] > 0 else 0.0
        ),
    )
    max_fit = max(item["concurrency"] for item in results)

    print("")
    print("=== summary ===")
    print(f"max stable concurrency: {max_fit}")
    print(
        f"best throughput concurrency: {best['concurrency']} "
        f"({best['successful_streams'] / best['elapsed_sec']:.2f} streams/s)"
    )

    for item in results:
        print(
            f"concurrency={item['concurrency']} "
            f"time={item['elapsed_sec']:.2f}s "
            f"success={item['successful_streams']}/{item['total_streams']} "
            f"peak_used={item['peak_used_mb']:.0f}MB "
            f"peak_reserved={item['peak_reserved_mb']:.0f}MB"
        )


if __name__ == "__main__":
    main()
