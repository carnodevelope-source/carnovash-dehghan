import argparse

from ultralytics import YOLO


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", type=str, default="weigths/yolov8-detector/yolov8-s-license-plate-detector.pt")
    parser.add_argument("--imgsz", type=int, default=416)
    parser.add_argument("--half", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--int8", action="store_true")
    parser.add_argument("--workspace", type=float, default=2.0)
    parser.add_argument("--device", type=int, default=0)
    return parser.parse_args()


def main():
    args = parse_args()
    model = YOLO(args.weights)
    model.export(
        format="engine",
        imgsz=args.imgsz,
        half=args.half,
        int8=args.int8,
        workspace=args.workspace,
        device=args.device,
    )


if __name__ == "__main__":
    main()
