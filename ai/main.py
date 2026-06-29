import argparse
import time

import cv2
import torch
from ultralytics import YOLO

from deep_text_recognition_benchmark.dtrb import DTRB
from light_plate_common import DEFAULT_OCR_CHARACTER_SET, draw_text_box_pil, postprocess_plate_text


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
    parser.add_argument("--input-image", type=str, default="io/input/582581_556.jpg")
    parser.add_argument("--threshold", type=float, default=0.7)
    parser.add_argument("--device", choices=("cuda", "auto"), default="cuda")
    parser.add_argument("--half", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--detector-imgsz", type=int, default=416)
    parser.add_argument("--max-detections", type=int, default=1)
    parser.add_argument("--save-output", action="store_true")
    return parser.parse_args()


def configure_runtime(opt):
    if opt.device in {"cuda", "auto"} and not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for this configuration, but no GPU is available.")


def clamp_bbox(bbox, width, height):
    x1, y1, x2, y2 = map(int, bbox)
    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(width, x2)
    y2 = min(height, y2)
    return x1, y1, x2, y2


def main():
    opt = parse_args()
    configure_runtime(opt)

    total_start_time = time.perf_counter()
    plate_detector = YOLO(opt.detector_weights)
    plate_recognizer = DTRB(opt.recognizer_weights, opt)

    image = cv2.imread(opt.input_image)
    if image is None:
        raise RuntimeError(f"Cannot read image: {opt.input_image}")

    height, width = image.shape[:2]
    inference_start_time = time.perf_counter()
    results = plate_detector.predict(
        image,
        conf=opt.threshold,
        device=opt.device,
        imgsz=opt.detector_imgsz,
        max_det=opt.max_detections,
        verbose=False,
        half=opt.half,
    )

    predictions = []
    for result in results:
        for i in range(len(result.boxes.xyxy)):
            x1, y1, x2, y2 = clamp_bbox(result.boxes.xyxy[i].tolist(), width, height)
            plate_image = image[y1:y2, x1:x2]
            if plate_image.size == 0:
                continue

            plate_image = cv2.resize(plate_image, (opt.imgW, opt.imgH), interpolation=cv2.INTER_AREA)
            plate_image = cv2.cvtColor(plate_image, cv2.COLOR_BGR2GRAY)
            raw_text, confidence = plate_recognizer.predict(plate_image, opt)
            text, persian_text = postprocess_plate_text(raw_text)
            predictions.append((x1, y1, x2, y2, text, persian_text, confidence))

    if opt.device == "cuda" and torch.cuda.is_available():
        torch.cuda.synchronize()
    inference_elapsed = time.perf_counter() - inference_start_time
    total_elapsed = time.perf_counter() - total_start_time

    if opt.save_output:
        rendered = image.copy()
        for x1, y1, x2, y2, text, persian_text, confidence in predictions:
            cv2.rectangle(rendered, (x1, y1), (x2, y2), (0, 255, 0), 2)
            label = text or "unknown"
            if text:
                label = f"{text} {confidence:.3f}"
            cv2.putText(rendered, label, (x1, max(24, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            if persian_text:
                rendered = draw_text_box_pil(rendered, persian_text, (x1, y2 + 8), font_size=28)
        cv2.imwrite("io/output/image_result_2.jpg", rendered)

    for x1, y1, x2, y2, text, persian_text, confidence in predictions:
        print(
            f"bbox=({x1},{y1},{x2},{y2}) text={text or '-'} "
            f"persian={persian_text or '-'} conf={confidence:.4f}"
        )

    print(f"Inference time (image to final result): {inference_elapsed:.4f} seconds")
    print(f"Total time (model load + inference): {total_elapsed:.4f} seconds")


if __name__ == "__main__":
    main()