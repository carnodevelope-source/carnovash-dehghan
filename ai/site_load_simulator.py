import argparse
import statistics
import threading
import time
from pathlib import Path
from typing import Dict, List

import cv2

from queued_realtime_plate_service import QueuedRealtimePlateService


class VideoFrameSource:
    def __init__(self, video_path: str, resize_width: int):
        self.video_path = video_path
        self.resize_width = resize_width
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open video: {video_path}")

    def read(self):
        ret, frame = self.cap.read()
        if not ret:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()
            if not ret:
                raise RuntimeError(f"Cannot loop video: {self.video_path}")

        if self.resize_width > 0 and frame.shape[1] > self.resize_width:
            scale = self.resize_width / frame.shape[1]
            frame = cv2.resize(frame, (self.resize_width, int(frame.shape[0] * scale)), interpolation=cv2.INTER_AREA)
        return frame

    def close(self):
        self.cap.release()


def percentile(values: List[float], q: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    index = (len(ordered) - 1) * q
    low = int(index)
    high = min(low + 1, len(ordered) - 1)
    weight = index - low
    return ordered[low] * (1.0 - weight) + ordered[high] * weight


def load_video_paths(args) -> List[str]:
    if args.input_list:
        return [line.strip() for line in Path(args.input_list).read_text(encoding="utf-8").splitlines() if line.strip()]
    return [str(path) for path in Path(args.video_dir).glob("*.mp4")]


def simulate_client(client_id: int, video_path: str, service: QueuedRealtimePlateService, args, metrics: Dict):
    source = VideoFrameSource(video_path, args.resize_width)
    latencies = []
    accepted = 0
    rejected = 0
    processed = 0
    stable_hits = 0
    ocr_runs = 0
    deadline = time.perf_counter() + args.duration_sec
    session_id = f"client-{client_id}"

    try:
        while time.perf_counter() < deadline:
            frame = source.read()
            started = time.perf_counter()
            response = service.submit_frame(session_id, frame, timeout_sec=args.request_timeout_sec)
            latencies.append(response["latency_ms"])
            if response.get("accepted"):
                accepted += 1
                processed += 1 if response.get("processed") else 0
                stable_hits += 1 if response.get("stable") else 0
                ocr_runs += 1 if response.get("reason") == "ocr_ran" else 0
            else:
                rejected += 1

            sleep_for = (args.send_interval_ms / 1000.0) - (time.perf_counter() - started)
            if sleep_for > 0:
                time.sleep(sleep_for)
    finally:
        source.close()
        metrics[session_id] = {
            "video": Path(video_path).name,
            "accepted": accepted,
            "rejected": rejected,
            "processed": processed,
            "stable_hits": stable_hits,
            "ocr_runs": ocr_runs,
            "latencies": latencies,
        }


def print_summary(client_metrics: Dict, service_metrics: Dict, elapsed_sec: float, args):
    all_latencies = [lat for item in client_metrics.values() for lat in item["latencies"]]
    total_accepted = sum(item["accepted"] for item in client_metrics.values())
    total_rejected = sum(item["rejected"] for item in client_metrics.values())
    total_processed = sum(item["processed"] for item in client_metrics.values())
    total_stable = sum(item["stable_hits"] for item in client_metrics.values())
    total_ocr_runs = sum(item["ocr_runs"] for item in client_metrics.values())

    print("")
    print("=== load summary ===")
    print(f"clients: {args.clients}")
    print(f"duration_sec: {elapsed_sec:.2f}")
    print(f"send_interval_ms: {args.send_interval_ms}")
    print(f"total_requests: {total_accepted + total_rejected}")
    print(f"accepted: {total_accepted}")
    print(f"rejected: {total_rejected}")
    print(f"processed_by_gpu_path: {total_processed}")
    print(f"stable_results: {total_stable}")
    print(f"ocr_runs: {total_ocr_runs}")
    print(f"throughput_req_per_sec: {(total_accepted + total_rejected) / elapsed_sec:.2f}")
    print(f"accepted_req_per_sec: {total_accepted / elapsed_sec:.2f}")
    print(f"mean_latency_ms: {statistics.mean(all_latencies):.2f}" if all_latencies else "mean_latency_ms: 0.00")
    print(f"p50_latency_ms: {percentile(all_latencies, 0.50):.2f}")
    print(f"p95_latency_ms: {percentile(all_latencies, 0.95):.2f}")
    print(f"p99_latency_ms: {percentile(all_latencies, 0.99):.2f}")
    print(f"gpu_batches: {service_metrics['gpu_batches']}")
    print(f"avg_gpu_batch_size: {service_metrics['avg_batch_size']:.2f}")
    print(f"detector_frames: {service_metrics['detector_frames']}")
    print(f"returned_without_gpu: {service_metrics['returned_without_gpu']}")
    print(f"queue_full_drops: {service_metrics['dropped_queue_full']}")
    print(f"gpu_used_mb: {service_metrics['gpu_used_mb']:.0f}")
    print(f"gpu_reserved_mb: {service_metrics['gpu_reserved_mb']:.0f}")
    print(f"gpu_peak_mb: {service_metrics['gpu_peak_mb']:.0f}")
    print("")
    print("=== client breakdown ===")
    for session_id, item in sorted(client_metrics.items()):
        print(
            f"{session_id} video={item['video']} accepted={item['accepted']} rejected={item['rejected']} "
            f"processed={item['processed']} ocr_runs={item['ocr_runs']} "
            f"p95={percentile(item['latencies'], 0.95):.2f}ms"
        )

    print("")
    print("=== tuning advice ===")
    if service_metrics["dropped_queue_full"] > 0:
        print("queue is overflowing: increase send interval, lower clients, or raise keyframe interval")
    if percentile(all_latencies, 0.95) > 300:
        print("p95 latency is high: raise --keyframe-interval or lower --send-interval-ms pressure")
    if service_metrics["avg_batch_size"] < 2.0 and args.clients > 1:
        print("GPU batching is weak: raise --batch-wait-ms slightly to merge more concurrent frames")
    if total_ocr_runs / max(1, total_accepted) > 0.5:
        print("OCR runs are frequent: raise --ocr-interval to reuse plate text longer")
    if service_metrics["gpu_peak_mb"] > 0 and service_metrics["gpu_peak_mb"] < 0.6 * service_metrics["gpu_reserved_mb"]:
        print("reserved memory is much higher than used memory: long-lived service is fine; avoid multi-process GPU workers")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video-dir", type=str, default="VID")
    parser.add_argument("--input-list", type=str, default="")
    parser.add_argument("--clients", type=int, default=8)
    parser.add_argument("--duration-sec", type=int, default=20)
    parser.add_argument("--send-interval-ms", type=int, default=250)
    parser.add_argument("--request-timeout-sec", type=float, default=5.0)
    parser.add_argument("--resize-width", type=int, default=640)
    parser.add_argument("--detector-weights", type=str, default="weigths/yolov8-detector/yolov8-s-license-plate-detector.pt")
    parser.add_argument("--recognizer-weights", type=str, default="weigths/dtrb-recoginzer/dtrb-None-VGG-BiLSTM-CTC-license-plate-recognizer.pth")
    parser.add_argument("--detector-imgsz", type=int, default=416)
    parser.add_argument("--threshold", type=float, default=0.7)
    parser.add_argument("--max-detections", type=int, default=1)
    parser.add_argument("--keyframe-interval", type=int, default=4)
    parser.add_argument("--ocr-interval", type=int, default=12)
    parser.add_argument("--stable-hits", type=int, default=2)
    parser.add_argument("--thumb-diff-threshold", type=float, default=2.0)
    parser.add_argument("--min-box-area", type=int, default=800)
    parser.add_argument("--max-batch-size", type=int, default=8)
    parser.add_argument("--batch-wait-ms", type=int, default=12)
    parser.add_argument("--max-queue-size", type=int, default=256)
    return parser.parse_args()


def main():
    args = parse_args()
    video_paths = load_video_paths(args)
    if not video_paths:
        raise RuntimeError("No input videos found for simulation.")

    service = QueuedRealtimePlateService(
        detector_weights=args.detector_weights,
        recognizer_weights=args.recognizer_weights,
        detector_imgsz=args.detector_imgsz,
        threshold=args.threshold,
        max_detections=args.max_detections,
        keyframe_interval=args.keyframe_interval,
        ocr_interval=args.ocr_interval,
        stable_hits=args.stable_hits,
        thumb_diff_threshold=args.thumb_diff_threshold,
        min_box_area=args.min_box_area,
        max_batch_size=args.max_batch_size,
        batch_wait_ms=args.batch_wait_ms,
        max_queue_size=args.max_queue_size,
    )

    metrics: Dict = {}
    threads: List[threading.Thread] = []
    started = time.perf_counter()

    try:
        for client_id in range(1, args.clients + 1):
            video_path = video_paths[(client_id - 1) % len(video_paths)]
            thread = threading.Thread(
                target=simulate_client,
                args=(client_id, video_path, service, args, metrics),
                daemon=True,
            )
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()
    finally:
        elapsed = time.perf_counter() - started
        service_metrics = service.get_metrics()
        service.shutdown()

    print_summary(metrics, service_metrics, elapsed, args)


if __name__ == "__main__":
    main()
