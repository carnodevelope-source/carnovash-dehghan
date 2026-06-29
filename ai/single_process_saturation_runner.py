import argparse
import contextlib
import io
import re
import time
from collections import Counter, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Deque, List, Tuple

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
    job_id: int
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


def expand_inputs(input_videos: List[str], input_list: str) -> List[str]:
    videos = []

    for item in input_videos:
        if item:
            videos.append(str(Path(item)))

    if input_list:
        with open(input_list, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    videos.append(str(Path(line)))

    if not videos:
        raise ValueError("No videos provided. Use --input-videos or --input-list.")

    return videos


def open_stream(stream_id: int, job_id: int, input_video: str) -> StreamState:
    cap = cv2.VideoCapture(input_video)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {input_video}")
    return StreamState(stream_id=stream_id, job_id=job_id, input_video=input_video, cap=cap)


def close_stream(stream: StreamState) -> None:
    if stream.cap is not None:
        stream.cap.release()


def process_active_streams(active_streams: List[StreamState], detector, recognizer, opt) -> List[StreamState]:
    frames = []
    frame_streams = []

    for stream in list(active_streams):
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
        return []

    results = detector.predict(frames, verbose=False, stream=False)
    finished_streams = []

    for result, (stream, frame) in zip(results, frame_streams):
        height, width = frame.shape[:2]

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
                finished_streams.append(stream)
                break

    return finished_streams


def probe_max_concurrency(video_paths: List[str], detector, recognizer, opt) -> int:
    last_stable = 0

    for concurrency in range(1, opt.max_probe_concurrency + 1):
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.reset_peak_memory_stats()

        active = []
        try:
            for idx in range(concurrency):
                active.append(open_stream(idx + 1, idx + 1, video_paths[idx % len(video_paths)]))

            session_start = time.time()
            while active:
                finished = process_active_streams(active, detector, recognizer, opt)
                for stream in list(active):
                    if stream.status != "running":
                        close_stream(stream)
                        active.remove(stream)

                if time.time() - session_start > opt.probe_timeout_sec:
                    raise RuntimeError("probe timeout")

            stats = get_gpu_stats()
            print(
                f"[probe] concurrency={concurrency} stable "
                f"peak={stats['peak_mb']:.0f}MB reserved={stats['reserved_mb']:.0f}MB"
            )
            last_stable = concurrency

        except RuntimeError as exc:
            message = str(exc).lower()
            for stream in active:
                close_stream(stream)
            if "out of memory" in message:
                print(f"[probe] OOM at concurrency={concurrency}")
                break
            raise

    if last_stable == 0:
        raise RuntimeError("No stable concurrency found")

    return last_stable


def build_job_queue(video_paths: List[str], total_jobs: int, cycle_inputs: bool) -> Deque[Tuple[int, str]]:
    jobs = deque()

    if cycle_inputs:
        for job_id in range(1, total_jobs + 1):
            jobs.append((job_id, video_paths[(job_id - 1) % len(video_paths)]))
    else:
        limited = video_paths[:total_jobs]
        for job_id, path in enumerate(limited, start=1):
            jobs.append((job_id, path))

    return jobs


def run_saturation(video_paths: List[str], detector, recognizer, opt, concurrency: int) -> None:
    job_queue = build_job_queue(video_paths, opt.total_jobs, opt.cycle_inputs)
    active_streams: List[StreamState] = []
    next_stream_id = 1
    completed_jobs = 0
    started_jobs = 0
    run_start = time.time()
    peak_used_mb = 0.0
    peak_reserved_mb = 0.0

    def refill():
        nonlocal next_stream_id, started_jobs
        while len(active_streams) < concurrency and job_queue:
            job_id, path = job_queue.popleft()
            stream = open_stream(next_stream_id, job_id, path)
            next_stream_id += 1
            started_jobs += 1
            active_streams.append(stream)
            print(f"[start] job={job_id} stream={stream.stream_id} file={Path(path).name}")

    refill()

    while active_streams:
        try:
            finished = process_active_streams(active_streams, detector, recognizer, opt)
        except RuntimeError as exc:
            if "out of memory" in str(exc).lower():
                print(f"[run] OOM at active={len(active_streams)}. stopping safely.")
                break
            raise

        for stream in list(active_streams):
            if stream.status != "running":
                elapsed = time.time() - run_start
                completed_jobs += 1
                print(
                    f"[done] job={stream.job_id} status={stream.status} plate={stream.matched_plate or '-'} "
                    f"frames={stream.frames_read} time_since_start={elapsed:.2f}s"
                )
                close_stream(stream)
                active_streams.remove(stream)

        refill()

        stats = get_gpu_stats()
        peak_used_mb = max(peak_used_mb, stats["used_mb"], stats["peak_mb"])
        peak_reserved_mb = max(peak_reserved_mb, stats["reserved_mb"])

        if opt.gpu_report_every > 0 and completed_jobs % opt.gpu_report_every == 0 and completed_jobs > 0:
            print(
                f"[gpu] completed={completed_jobs}/{opt.total_jobs} active={len(active_streams)} "
                f"used={stats['used_mb']:.0f}MB reserved={stats['reserved_mb']:.0f}MB "
                f"peak={stats['peak_mb']:.0f}MB"
            )

    elapsed_total = time.time() - run_start
    print("")
    print("=== saturation summary ===")
    print(f"stable concurrency used: {concurrency}")
    print(f"started jobs: {started_jobs}")
    print(f"completed jobs: {completed_jobs}")
    print(f"elapsed seconds: {elapsed_total:.2f}")
    print(f"throughput jobs/s: {(completed_jobs / elapsed_total) if elapsed_total > 0 else 0.0:.2f}")
    print(f"peak used MB: {peak_used_mb:.0f}")
    print(f"peak reserved MB: {peak_reserved_mb:.0f}")


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
    parser.add_argument("--cycle-inputs", action="store_true")
    parser.add_argument("--total-jobs", type=int, default=20)
    parser.add_argument("--max-probe-concurrency", type=int, default=10)
    parser.add_argument("--probe-timeout-sec", type=float, default=30.0)
    parser.add_argument("--success-count", type=int, default=3)
    parser.add_argument("--threshold", type=float, default=0.6)
    parser.add_argument("--process-every", type=int, default=1)
    parser.add_argument("--gpu-report-every", type=int, default=5)

    return parser.parse_args()


def main():
    opt = parse_args()
    video_paths = expand_inputs(opt.input_videos, opt.input_list)

    print("loading detector once ...")
    detector = YOLO(opt.detector_weights)
    print("loading recognizer once ...")
    recognizer = DTRB(opt.recognizer_weights, opt)

    print("probing max stable concurrency ...")
    stable_concurrency = probe_max_concurrency(video_paths, detector, recognizer, opt)
    print(f"stable concurrency found: {stable_concurrency}")

    print("starting back-to-back saturation run ...")
    run_saturation(video_paths, detector, recognizer, opt, stable_concurrency)


if __name__ == "__main__":
    main()
