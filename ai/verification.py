import argparse
from difflib import SequenceMatcher

import cv2
from ultralytics import YOLO

from database.Creating_data import Database
from deep_text_recognition_benchmark.dtrb import DTRB
from light_plate_common import DEFAULT_OCR_CHARACTER_SET, canonicalize_plate_text, clamp_bbox


parser = argparse.ArgumentParser()
parser.add_argument("--workers", type=int, help="number of data loading workers", default=0)
parser.add_argument("--batch_size", type=int, default=192, help="input batch size")
parser.add_argument("--batch_max_length", type=int, default=25, help="maximum-label-length")
parser.add_argument("--imgH", type=int, default=32, help="the height of the input image")
parser.add_argument("--imgW", type=int, default=100, help="the width of the input image")
parser.add_argument("--rgb", action="store_true", help="use rgb input")
parser.add_argument("--character", type=str, default=DEFAULT_OCR_CHARACTER_SET, help="character label")
parser.add_argument("--sensitive", action="store_true", help="for sensitive character mode")
parser.add_argument("--PAD", action="store_true", help="whether to keep ratio then pad for image resize")
parser.add_argument("--Transformation", type=str, default="TPS", help="Transformation stage. None|TPS")
parser.add_argument("--FeatureExtraction", type=str, default="ResNet", help="FeatureExtraction stage. VGG|RCNN|ResNet")
parser.add_argument("--SequenceModeling", type=str, default="BiLSTM", help="SequenceModeling stage. None|BiLSTM")
parser.add_argument("--Prediction", type=str, default="Attn", help="Prediction stage. CTC|Attn")
parser.add_argument("--num_fiducial", type=int, default=20, help="number of fiducial points of TPS-STN")
parser.add_argument("--input_channel", type=int, default=1, help="the number of input channel of Feature extractor")
parser.add_argument("--output_channel", type=int, default=512, help="the number of output channel of Feature extractor")
parser.add_argument("--hidden_size", type=int, default=256, help="the size of the LSTM hidden state")
parser.add_argument("--detector-weights", type=str, default="weigths/yolov8-detector/yolov8-s-license-plate-detector.pt")
parser.add_argument("--recognizer-weights", type=str, default="weigths/dtrb-recoginzer/dtrb-None-VGG-BiLSTM-CTC-license-plate-recognizer.pth")
parser.add_argument("--input-image", type=str, default="io/input/1.jpg")
parser.add_argument("--threshold", type=float, default=0.7)

opt = parser.parse_args()


def sequence_matcher(left, right):
    return SequenceMatcher(None, left, right).ratio()


database = Database()
plate_detector = YOLO(opt.detector_weights)
plates = [canonicalize_plate_text(item[2]) for item in database.get_Plake_text()]
plate_recognizer = DTRB(opt.recognizer_weights, opt)
image = cv2.imread(opt.input_image)
results = plate_detector.predict(image)

for result in results:
    for i in range(len(result.boxes.xyxy)):
        if result.boxes.conf[i] <= opt.threshold:
            continue

        x1, y1, x2, y2 = clamp_bbox(result.boxes.xyxy[i].tolist(), image.shape[1], image.shape[0])
        plate_image = image[y1:y2, x1:x2].copy()
        if plate_image.size == 0:
            continue

        cv2.imwrite(f"io/output/plate_image_result_{i}.jpg", plate_image)
        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 4)
        plate_image = cv2.resize(plate_image, (100, 32))
        plate_image = cv2.cvtColor(plate_image, cv2.COLOR_BGR2GRAY)
        ocr_text, _ = plate_recognizer.predict(plate_image, opt)
        label = canonicalize_plate_text(ocr_text)
        for database_plate in plates:
            if sequence_matcher(database_plate, label) > 0.8:
                print("True")
                break
        else:
            print("False")
            break

cv2.imwrite("io/output/image_result.jpg", image)