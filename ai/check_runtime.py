import os
import platform
import sys
from pathlib import Path

import cv2
import torch


ROOT = Path(__file__).resolve().parent


def check_path(path_str: str) -> str:
    return "OK" if Path(path_str).exists() else "MISSING"


def main():
    detector_weights = ROOT / "weigths" / "yolov8-detector" / "yolov8-s-license-plate-detector.pt"
    recognizer_weights = (
        ROOT / "weigths" / "dtrb-recoginzer" / "dtrb-None-VGG-BiLSTM-CTC-license-plate-recognizer.pth"
    )
    sample_videos = [ROOT / "vid1.mp4", ROOT / "vid2.mp4"]

    print("=== Runtime Check ===")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Platform: {platform.platform()}")
    print(f"OpenCV: {cv2.__version__}")
    print(f"Torch: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")

    if torch.cuda.is_available():
        device_index = torch.cuda.current_device()
        props = torch.cuda.get_device_properties(device_index)
        total_mb = props.total_memory / (1024 ** 2)
        print(f"GPU name: {props.name}")
        print(f"GPU VRAM MB: {total_mb:.0f}")
        if total_mb <= 2300:
            print("Recommended batch max_concurrent: 1")
        elif total_mb <= 4600:
            print("Recommended batch max_concurrent: 2")
        else:
            print("Recommended batch max_concurrent: 3")
    else:
        print("Recommended batch max_concurrent: 1")

    print("")
    print("=== File Check ===")
    print(f"Detector weights: {check_path(detector_weights)}")
    print(f"Recognizer weights: {check_path(recognizer_weights)}")

    for video_path in sample_videos:
        print(f"{video_path.name}: {check_path(video_path)}")

    print("")
    print("=== Output Dirs ===")
    os.makedirs(ROOT / "io" / "output", exist_ok=True)
    print(f"Output dir: OK ({ROOT / 'io' / 'output'})")


if __name__ == "__main__":
    main()
