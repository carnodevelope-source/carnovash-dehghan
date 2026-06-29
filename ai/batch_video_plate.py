import argparse
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

import cv2
import torch
from ultralytics import YOLO

from deep_text_recognition_benchmark.dtrb import DTRB
from light_plate_common import (
    DEFAULT_OCR_CHARACTER_SET,
    clamp_bbox,
    configure_torch_runtime,
    postprocess_plate_text,
    reuse_cached_text,
)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--batch_size", type=int, default=1)
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
    parser.add_argument("--detector-weights", type=str, default="weigths/yolov8-detector/yolov8-s-license-plate-detector.pt")
    parser.add_argument("--recognizer-weights", type=str, default="weigths/dtrb-recoginzer/dtrb-None-VGG-BiLSTM-CTC-license-plate-recognizer.pth")
    parser.add_argument("--input-videos", nargs="*", default=[])
    parser.add_argument("--input-list", type=str, default="")
    parser.add_argument("--output-dir", type=str, default="io/output/batch_videos")
    parser.add_argument("--report-md", type=str, default="io/output/batch_report.md")
    parser.add_argument("--threshold", type=float, default=0.7)
    parser.add_argument("--device", choices=("cuda", "auto"), default="cuda")
    parser.add_argument("--half", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--detector-imgsz", type=int, default=416)
    parser.add_argument("--process-every", type=int, default=4)
    parser.add_argument("--ocr-every", type=int, default=12)
    parser.add_argument("--cache-iou", type=float, default=0.75)
    parser.add_argument("--max-detections", type=int, default=1)
    parser.add_argument("--min-box-area", type=int, default=800)
    parser.add_argument("--success-count", type=int, default=3)
    parser.add_argument("--write-output-video", action="store_true")
    return parser.parse_args()


def load_jobs(args):
    jobs = [item for item in args.input_videos if item]
    if args.input_list:
        with open(args.input_list, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    jobs.append(line)
    if not jobs:
        raise ValueError("No input videos provided. Use --input-videos or --input-list.")
    return jobs


def make_output_path(output_dir: str, job_index: int, input_video: str) -> str:
    return str(Path(output_dir) / f"{job_index:02d}_{Path(input_video).stem}_result.mp4")


def process_video(job_index, input_video, detector, recognizer, args):
    cap = cv2.VideoCapture(input_video)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {input_video}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    output_video = make_output_path(args.output_dir, job_index, input_video)
    writer = None
    if args.write_output_video:
        Path(args.output_dir).mkdir(parents=True, exist_ok=True)
        writer = cv2.VideoWriter(output_video, cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))

    start = time.perf_counter()
    frame_index = 0
    frames_processed = 0
    detections_seen = 0
    unique_plates = Counter()
    cache = []
    matched_plate = ""
    matched_plate_persian = ""
    status = "completed_without_match"
    stop_reason = "video_ended"

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_index % args.process_every == 0:
            frames_processed += 1
            results = detector.predict(
                frame,
                conf=args.threshold,
                device=args.device,
                imgsz=args.detector_imgsz,
                max_det=args.max_detections,
                verbose=False,
                half=args.half,
            )
            for result in results:
                for i in range(len(result.boxes.xyxy)):
                    bbox = clamp_bbox(result.boxes.xyxy[i].tolist(), width, height)
                    x1, y1, x2, y2 = bbox
                    if (x2 - x1) * (y2 - y1) < args.min_box_area:
                        continue

                    cached = reuse_cached_text(cache, bbox, frame_index, args.ocr_every, args.cache_iou)
                    if cached is not None:
                        raw_text = cached["raw_text"]
                        persian_text = cached["persian_text"]
                    else:
                        plate_crop = frame[y1:y2, x1:x2]
                        if plate_crop.size == 0:
                            continue
                        plate_image = cv2.resize(plate_crop, (args.imgW, args.imgH), interpolation=cv2.INTER_AREA)
                        plate_image = cv2.cvtColor(plate_image, cv2.COLOR_BGR2GRAY)
                        ocr_text, ocr_conf = recognizer.predict(plate_image, args)
                        raw_text, persian_text = postprocess_plate_text(ocr_text)
                        if raw_text:
                            cache.append(
                                {
                                    "bbox": bbox,
                                    "raw_text": raw_text,
                                    "persian_text": persian_text,
                                    "ocr_conf": ocr_conf,
                                    "frame_index": frame_index,
                                }
                            )

                    if not raw_text:
                        continue

                    detections_seen += 1
                    unique_plates[raw_text] += 1
                    if unique_plates[raw_text] >= args.success_count:
                        matched_plate = raw_text
                        matched_plate_persian = persian_text
                        status = "success"
                        stop_reason = f"matched_{args.success_count}_times"
                        break

                if status == "success":
                    break

            cache = [item for item in cache if frame_index - item["frame_index"] <= args.ocr_every]

        if writer is not None:
            writer.write(frame)

        frame_index += 1
        if status == "success":
            break

    cap.release()
    if writer is not None:
        writer.release()

    elapsed = time.perf_counter() - start
    return {
        "job_index": job_index,
        "input_video": input_video,
        "output_video": output_video if writer is not None else "",
        "status": status,
        "stop_reason": stop_reason,
        "matched_plate": matched_plate,
        "matched_plate_persian": matched_plate_persian,
        "frames_read": frame_index,
        "frames_processed": frames_processed,
        "detections_seen": detections_seen,
        "unique_plate_count": len(unique_plates),
        "top_candidates": unique_plates.most_common(5),
        "elapsed_sec": elapsed,
        "avg_fps": (frame_index / elapsed) if elapsed > 0 else 0.0,
    }


def build_report(results, report_path, args):
    lines = [
        "# Batch Video Plate Report",
        "",
        f"- Generated at: {datetime.now().isoformat(timespec='seconds')}",
        f"- Jobs: {len(results)}",
        f"- Process every N frames: {args.process_every}",
        f"- OCR cache frames: {args.ocr_every}",
        f"- Max detections per processed frame: {args.max_detections}",
        f"- Detector image size: {args.detector_imgsz}",
        f"- Write output video: {args.write_output_video}",
        "",
        "| Job | Input | Status | Plate | Frames | Processed | Detections | Seconds | Avg FPS |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]

    for item in results:
        lines.append(
            f"| {item['job_index']} | {Path(item['input_video']).name} | {item['status']} | "
            f"{item['matched_plate'] or '-'} | {item['frames_read']} | {item['frames_processed']} | "
            f"{item['detections_seen']} | {item['elapsed_sec']:.2f} | {item['avg_fps']:.2f} |"
        )

    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    args = parse_args()
    configure_torch_runtime(args.device, 1)
    jobs = load_jobs(args)
    detector = YOLO(args.detector_weights)
    recognizer = DTRB(args.recognizer_weights, args)
    results = []

    for job_index, input_video in enumerate(jobs, start=1):
        result = process_video(job_index, input_video, detector, recognizer, args)
        results.append(result)
        print(
            f"job {job_index} finished: status={result['status']} "
            f"plate={result['matched_plate'] or '-'} time={result['elapsed_sec']:.2f}s"
        )

    build_report(results, args.report_md, args)
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    print(f"Report saved to: {args.report_md}")


if __name__ == "__main__":
    main()