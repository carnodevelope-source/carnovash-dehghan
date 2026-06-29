import argparse
import os

import cv2
import torch
from ultralytics import YOLO

from deep_text_recognition_benchmark.dtrb import DTRB
from light_plate_common import (
    DEFAULT_OCR_CHARACTER_SET,
    clamp_bbox,
    configure_torch_runtime,
    draw_text_box_pil,
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
    parser.add_argument("--input-video", type=str, required=True)
    parser.add_argument("--output-video", type=str, default="io/output/video_result.mp4")
    parser.add_argument("--threshold", type=float, default=0.7)
    parser.add_argument("--device", choices=("cuda", "auto"), default="cuda")
    parser.add_argument("--half", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--detector-imgsz", type=int, default=416)
    parser.add_argument("--process-every", type=int, default=4)
    parser.add_argument("--ocr-every", type=int, default=12)
    parser.add_argument("--cache-iou", type=float, default=0.75)
    parser.add_argument("--max-detections", type=int, default=1)
    parser.add_argument("--min-box-area", type=int, default=800)
    parser.add_argument("--font", type=str, default="")
    parser.add_argument("--show", action="store_true")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--write-output-video", action="store_true")
    return parser.parse_args()


def process_frame(frame, detector, recognizer, opt, frame_index, cache):
    height, width = frame.shape[:2]
    detections = []
    results = detector.predict(
        frame,
        conf=opt.threshold,
        device=opt.device,
        imgsz=opt.detector_imgsz,
        max_det=opt.max_detections,
        verbose=False,
        half=opt.half,
    )

    for result in results:
        for i in range(len(result.boxes.xyxy)):
            bbox = clamp_bbox(result.boxes.xyxy[i].tolist(), width, height)
            x1, y1, x2, y2 = bbox
            if (x2 - x1) * (y2 - y1) < opt.min_box_area:
                continue

            cached = reuse_cached_text(cache, bbox, frame_index, opt.ocr_every, opt.cache_iou)
            if cached is not None:
                detections.append(
                    {
                        "bbox": bbox,
                        "raw_text": cached["raw_text"],
                        "persian_text": cached["persian_text"],
                        "ocr_conf": cached["ocr_conf"],
                    }
                )
                continue

            plate_crop = frame[y1:y2, x1:x2]
            if plate_crop.size == 0:
                continue

            plate_image = cv2.resize(plate_crop, (opt.imgW, opt.imgH), interpolation=cv2.INTER_AREA)
            plate_image = cv2.cvtColor(plate_image, cv2.COLOR_BGR2GRAY)
            ocr_text, ocr_conf = recognizer.predict(plate_image, opt)
            raw_text, persian_text = postprocess_plate_text(ocr_text)
            detections.append(
                {
                    "bbox": bbox,
                    "raw_text": raw_text,
                    "persian_text": persian_text,
                    "ocr_conf": ocr_conf,
                }
            )
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

    cache[:] = [item for item in cache if frame_index - item["frame_index"] <= opt.ocr_every]
    return detections


def render_frame(frame, detections, opt):
    for det in detections:
        x1, y1, x2, y2 = det["bbox"]
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        label = det["raw_text"] or "plate"
        if det["raw_text"]:
            label = f"{det['raw_text']} {det['ocr_conf']:.3f}"
        cv2.putText(frame, label, (x1, max(24, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        if det["persian_text"]:
            frame = draw_text_box_pil(frame, det["persian_text"], (x1, max(2, y1 - 44)), font_path=opt.font, font_size=28)
    return frame


def main():
    opt = parse_args()
    configure_torch_runtime(opt.device, 1)
    detector = YOLO(opt.detector_weights)
    recognizer = DTRB(opt.recognizer_weights, opt)

    cap = cv2.VideoCapture(opt.input_video)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {opt.input_video}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    writer = None
    if opt.write_output_video:
        os.makedirs(os.path.dirname(opt.output_video), exist_ok=True)
        writer = cv2.VideoWriter(opt.output_video, cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))

    frame_index = 0
    cache = []
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        detections = []
        if frame_index % opt.process_every == 0:
            detections = process_frame(frame, detector, recognizer, opt, frame_index, cache)

        if opt.render:
            frame = render_frame(frame, detections, opt)

        if writer is not None:
            writer.write(frame)

        if opt.show:
            cv2.imshow("video_plate", frame)
            if cv2.waitKey(1) & 0xFF == 27:
                break

        frame_index += 1

    cap.release()
    if writer is not None:
        writer.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()