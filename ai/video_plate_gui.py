import argparse
import queue
import threading
import time
import tkinter as tk
from collections import Counter, deque
from dataclasses import dataclass, field
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import cv2
from ultralytics import YOLO

from deep_text_recognition_benchmark.dtrb import DTRB
from light_plate_common import DEFAULT_OCR_CHARACTER_SET, clamp_bbox, configure_torch_runtime, postprocess_plate_text, reuse_cached_text


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


@dataclass
class VideoJob:
    job_id: int
    video_path: str
    cap: cv2.VideoCapture
    status: str = "queued"
    frame_index: int = 0
    frames_processed: int = 0
    detections_seen: int = 0
    last_text: str = ""
    last_persian: str = ""
    last_confidence: float = 0.0
    plate_counts: Counter = field(default_factory=Counter)
    cache: list = field(default_factory=list)
    started_at: float = 0.0


class VideoJobScheduler:
    def __init__(
        self,
        detector_weights: str,
        recognizer_weights: str,
        event_queue: queue.Queue,
        detector_imgsz: int = 416,
        threshold: float = 0.7,
        max_detections: int = 1,
        process_every: int = 10,
        ocr_every: int = 20,
        success_count: int = 3,
        min_box_area: int = 800,
        cache_iou: float = 0.75,
        max_parallel: int = 2,
    ):
        configure_torch_runtime("cuda", 1)
        self.args = build_runtime_args()
        self.detector = YOLO(detector_weights)
        self.recognizer = DTRB(recognizer_weights, self.args)
        self.event_queue = event_queue
        self.detector_imgsz = detector_imgsz
        self.threshold = threshold
        self.max_detections = max_detections
        self.process_every = process_every
        self.ocr_every = ocr_every
        self.success_count = success_count
        self.min_box_area = min_box_area
        self.cache_iou = cache_iou
        self.max_parallel = max(1, max_parallel)
        self.pending_jobs = deque()
        self.active_jobs = []
        self.job_id = 0
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.worker_thread = threading.Thread(target=self._loop, daemon=True)
        self.worker_thread.start()

    def enqueue(self, video_path: str) -> int:
        with self.lock:
            self.job_id += 1
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise RuntimeError(f"Cannot open video: {video_path}")
            job = VideoJob(job_id=self.job_id, video_path=video_path, cap=cap)
            self.pending_jobs.append(job)
            self.event_queue.put(("queued", {"job_id": job.job_id, "video_path": video_path}))
            return job.job_id

    def shutdown(self):
        self.stop_event.set()
        self.worker_thread.join(timeout=2.0)
        with self.lock:
            for job in self.pending_jobs:
                job.cap.release()
            for job in self.active_jobs:
                job.cap.release()

    def set_max_parallel(self, value: int):
        with self.lock:
            self.max_parallel = max(1, value)

    def snapshot(self):
        with self.lock:
            return {
                "queued": len(self.pending_jobs),
                "running": len(self.active_jobs),
                "max_parallel": self.max_parallel,
            }

    def _loop(self):
        while not self.stop_event.is_set():
            self._refill_active()
            if not self.active_jobs:
                time.sleep(0.05)
                continue

            batched_frames = []
            batched_jobs = []

            with self.lock:
                current_jobs = list(self.active_jobs)

            for job in current_jobs:
                ret, frame = job.cap.read()
                if not ret:
                    self._finish_job(job, "completed_without_match")
                    continue

                if job.frame_index % self.process_every == 0:
                    job.frames_processed += 1
                    batched_frames.append(frame)
                    batched_jobs.append((job, frame))

                job.frame_index += 1

            if not batched_frames:
                continue

            results = self.detector.predict(
                batched_frames,
                conf=self.threshold,
                device="cuda",
                imgsz=self.detector_imgsz,
                max_det=self.max_detections,
                verbose=False,
                half=True,
                stream=False,
            )

            for result, (job, frame) in zip(results, batched_jobs):
                finished = self._process_detection_result(job, frame, result)
                if finished:
                    self._finish_job(job, "success")

    def _refill_active(self):
        with self.lock:
            while len(self.active_jobs) < self.max_parallel and self.pending_jobs:
                job = self.pending_jobs.popleft()
                job.status = "running"
                job.started_at = time.perf_counter()
                self.active_jobs.append(job)
                self.event_queue.put(
                    (
                        "started",
                        {
                            "job_id": job.job_id,
                            "video_path": job.video_path,
                            "running": len(self.active_jobs),
                            "queued": len(self.pending_jobs),
                        },
                    )
                )

    def _finish_job(self, job: VideoJob, status: str):
        with self.lock:
            if job in self.active_jobs:
                self.active_jobs.remove(job)
        job.status = status
        job.cap.release()
        elapsed = time.perf_counter() - job.started_at if job.started_at else 0.0
        self.event_queue.put(
            (
                "finished",
                {
                    "job_id": job.job_id,
                    "video_path": job.video_path,
                    "status": status,
                    "plate_text": job.last_text,
                    "plate_persian": job.last_persian,
                    "confidence": job.last_confidence,
                    "frames_processed": job.frames_processed,
                    "detections_seen": job.detections_seen,
                    "elapsed_sec": elapsed,
                },
            )
        )

    def _process_detection_result(self, job: VideoJob, frame, result) -> bool:
        height, width = frame.shape[:2]

        for i in range(len(result.boxes.xyxy)):
            bbox = clamp_bbox(result.boxes.xyxy[i].tolist(), width, height)
            x1, y1, x2, y2 = bbox
            if (x2 - x1) * (y2 - y1) < self.min_box_area:
                continue

            cached = reuse_cached_text(job.cache, bbox, job.frame_index, self.ocr_every, self.cache_iou)
            if cached is not None:
                raw_text = cached["raw_text"]
                persian_text = cached["persian_text"]
                confidence = cached["ocr_conf"]
            else:
                plate_crop = frame[y1:y2, x1:x2]
                if plate_crop.size == 0:
                    continue
                plate_image = cv2.resize(plate_crop, (self.args.imgW, self.args.imgH), interpolation=cv2.INTER_AREA)
                plate_image = cv2.cvtColor(plate_image, cv2.COLOR_BGR2GRAY)
                ocr_text, confidence = self.recognizer.predict(plate_image, self.args)
                raw_text, persian_text = postprocess_plate_text(ocr_text)
                if raw_text:
                    job.cache.append(
                        {
                            "bbox": bbox,
                            "raw_text": raw_text,
                            "persian_text": persian_text,
                            "ocr_conf": confidence,
                            "frame_index": job.frame_index,
                        }
                    )

            if not raw_text:
                continue

            job.detections_seen += 1
            job.last_text = raw_text
            job.last_persian = persian_text
            job.last_confidence = confidence
            job.plate_counts[raw_text] += 1
            if job.plate_counts[raw_text] >= self.success_count:
                return True

        job.cache = [item for item in job.cache if job.frame_index - item["frame_index"] <= self.ocr_every]
        return False


class VideoPlateGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Queued Plate Analyzer")
        self.root.geometry("860x560")
        self.selected_video = ""
        self.event_queue = queue.Queue()
        self.scheduler = None

        self.status_var = tk.StringVar(value="Loading models once on GPU...")
        self.video_var = tk.StringVar(value="No video selected")
        self.queue_var = tk.StringVar(value="queued=0 | running=0 | parallel=2")
        self.parallel_var = tk.IntVar(value=2)

        self._build_ui()
        self._load_scheduler_async()
        self.root.after(100, self._drain_events)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        container = ttk.Frame(self.root, padding=18)
        container.pack(fill="both", expand=True)

        ttk.Label(container, text="Queued Video Plate Analyzer", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(
            container,
            text="Select one video once. Each Start click queues a new processing job for the same video.",
        ).pack(anchor="w", pady=(4, 14))

        top = ttk.Frame(container)
        top.pack(fill="x")

        self.choose_button = ttk.Button(top, text="Choose Video Once", command=self._choose_video, state="disabled")
        self.choose_button.pack(side="left")

        self.start_button = ttk.Button(top, text="Start", command=self._enqueue_job, state="disabled")
        self.start_button.pack(side="left", padx=(8, 0))

        ttk.Label(top, text="Parallel slots").pack(side="left", padx=(16, 6))
        spin = ttk.Spinbox(top, from_=1, to=8, textvariable=self.parallel_var, width=5, command=self._update_parallel)
        spin.pack(side="left")

        ttk.Label(top, textvariable=self.status_var).pack(side="left", padx=(16, 0))

        ttk.Label(container, textvariable=self.video_var, font=("Consolas", 10)).pack(anchor="w", pady=(16, 8))
        ttk.Label(container, textvariable=self.queue_var, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 10))

        columns = ("job", "video", "status", "plate", "persian", "confidence", "elapsed", "processed")
        self.tree = ttk.Treeview(container, columns=columns, show="headings", height=18)
        self.tree.heading("job", text="Job")
        self.tree.heading("video", text="Video")
        self.tree.heading("status", text="Status")
        self.tree.heading("plate", text="Plate")
        self.tree.heading("persian", text="Persian")
        self.tree.heading("confidence", text="Confidence")
        self.tree.heading("elapsed", text="Seconds")
        self.tree.heading("processed", text="Frames")
        self.tree.column("job", width=60, anchor="center")
        self.tree.column("video", width=200)
        self.tree.column("status", width=110, anchor="center")
        self.tree.column("plate", width=90, anchor="center")
        self.tree.column("persian", width=120, anchor="center")
        self.tree.column("confidence", width=85, anchor="center")
        self.tree.column("elapsed", width=80, anchor="center")
        self.tree.column("processed", width=80, anchor="center")
        self.tree.pack(fill="both", expand=True)

    def _load_scheduler_async(self):
        threading.Thread(target=self._load_scheduler, daemon=True).start()

    def _load_scheduler(self):
        try:
            scheduler = VideoJobScheduler(
                detector_weights="weigths/yolov8-detector/yolov8-s-license-plate-detector.pt",
                recognizer_weights="weigths/dtrb-recoginzer/dtrb-None-VGG-BiLSTM-CTC-license-plate-recognizer.pth",
                event_queue=self.event_queue,
                max_parallel=self.parallel_var.get(),
            )
        except Exception as exc:
            message = str(exc)
            self.root.after(0, lambda msg=message: self._show_load_error(msg))
            return
        self.root.after(0, lambda loaded_scheduler=scheduler: self._scheduler_ready(loaded_scheduler))

    def _show_load_error(self, message: str):
        self.status_var.set("Model load failed.")
        messagebox.showerror("Load Error", message)

    def _scheduler_ready(self, scheduler: VideoJobScheduler):
        self.scheduler = scheduler
        self.status_var.set("Models loaded once on CUDA. Choose a video, then press Start any number of times.")
        self.choose_button.config(state="normal")

    def _choose_video(self):
        path = filedialog.askopenfilename(
            title="Choose video",
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv"), ("All files", "*.*")],
        )
        if not path:
            return
        self.selected_video = path
        self.video_var.set(path)
        self.start_button.config(state="normal")

    def _enqueue_job(self):
        if not self.scheduler or not self.selected_video:
            return
        try:
            job_id = self.scheduler.enqueue(self.selected_video)
        except Exception as exc:
            messagebox.showerror("Queue Error", str(exc))
            return
        self.status_var.set(f"Job {job_id} queued.")
        self._refresh_queue_label()

    def _update_parallel(self):
        if self.scheduler:
            self.scheduler.set_max_parallel(self.parallel_var.get())
            self._refresh_queue_label()

    def _refresh_queue_label(self):
        if not self.scheduler:
            return
        snap = self.scheduler.snapshot()
        self.queue_var.set(f"queued={snap['queued']} | running={snap['running']} | parallel={snap['max_parallel']}")

    def _drain_events(self):
        try:
            while True:
                event_name, payload = self.event_queue.get_nowait()
                if event_name == "queued":
                    self.tree.insert(
                        "",
                        0,
                        iid=str(payload["job_id"]),
                        values=(payload["job_id"], Path(payload["video_path"]).name, "queued", "-", "-", "-", "-", "-"),
                    )
                elif event_name == "started":
                    self.tree.item(
                        str(payload["job_id"]),
                        values=(payload["job_id"], Path(payload["video_path"]).name, "running", "-", "-", "-", "-", "-"),
                    )
                elif event_name == "finished":
                    self.tree.item(
                        str(payload["job_id"]),
                        values=(
                            payload["job_id"],
                            Path(payload["video_path"]).name,
                            payload["status"],
                            payload["plate_text"] or "-",
                            payload["plate_persian"] or "-",
                            f"{payload['confidence']:.3f}" if payload["confidence"] else "-",
                            f"{payload['elapsed_sec']:.2f}",
                            payload["frames_processed"],
                        ),
                    )
                    self.status_var.set(
                        f"Job {payload['job_id']} finished: {payload['plate_text'] or 'no plate'}"
                    )
                self._refresh_queue_label()
        except queue.Empty:
            pass

        self.root.after(100, self._drain_events)

    def _on_close(self):
        if self.scheduler:
            self.scheduler.shutdown()
        self.root.destroy()


def main():
    root = tk.Tk()
    style = ttk.Style(root)
    if "vista" in style.theme_names():
        style.theme_use("vista")
    VideoPlateGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
