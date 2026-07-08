import argparse
import base64
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import cv2
import numpy as np

from queued_realtime_plate_service import QueuedRealtimePlateService


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DETECTOR = BASE_DIR / "weigths" / "yolov8-detector" / "yolov8-s-license-plate-detector.pt"
DEFAULT_RECOGNIZER = BASE_DIR / "weigths" / "dtrb-recoginzer" / "dtrb-None-VGG-BiLSTM-CTC-license-plate-recognizer.pth"


def _decode_image(image_value: str):
    if not image_value:
        raise ValueError("image_base64 is required.")
    if "," in image_value and image_value.split(",", 1)[0].startswith("data:"):
        image_value = image_value.split(",", 1)[1]
    try:
        raw = base64.b64decode(image_value, validate=True)
    except Exception as exc:
        raise ValueError("image_base64 is not valid base64.") from exc
    image_array = np.frombuffer(raw, dtype=np.uint8)
    frame = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("image payload is not a readable image.")
    return frame


def _json_response(handler: BaseHTTPRequestHandler, status_code: int, payload: dict):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status_code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def make_handler(service: QueuedRealtimePlateService, started_at: float):
    class PlateRequestHandler(BaseHTTPRequestHandler):
        server_version = "CarWashPlateAI/1.0"

        def log_message(self, format_text, *args):
            print(f"[plate-ai] {self.address_string()} - {format_text % args}")

        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path != "/health":
                _json_response(self, 404, {"detail": "Not found."})
                return
            metrics = service.get_metrics()
            _json_response(
                self,
                200,
                {
                    "ok": True,
                    "uptime_sec": round(time.perf_counter() - started_at, 3),
                    "metrics": metrics,
                },
            )

        def do_POST(self):
            parsed = urlparse(self.path)
            if parsed.path != "/recognize":
                _json_response(self, 404, {"detail": "Not found."})
                return

            try:
                content_length = int(self.headers.get("Content-Length", "0") or "0")
                if content_length <= 0:
                    raise ValueError("Request body is empty.")
                payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
                session_id = str(payload.get("session_id") or "default").strip() or "default"
                timeout_sec = float(payload.get("timeout_sec") or 4.0)
                force_process = bool(payload.get("force_process", False))
                image_value = payload.get("image_base64") or payload.get("image_data_url") or ""
                frame = _decode_image(str(image_value))
                result = service.submit_frame(
                    session_id=session_id,
                    frame_bgr=frame,
                    timeout_sec=timeout_sec,
                    force_process=force_process,
                )
            except ValueError as exc:
                _json_response(self, 400, {"accepted": False, "detail": str(exc)})
                return
            except Exception as exc:
                _json_response(self, 500, {"accepted": False, "detail": str(exc)})
                return

            _json_response(self, 200, result)

    return PlateRequestHandler


def main():
    parser = argparse.ArgumentParser(description="HTTP bridge for the carwash plate-recognition AI.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--detector", default=str(DEFAULT_DETECTOR))
    parser.add_argument("--recognizer", default=str(DEFAULT_RECOGNIZER))
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--batch-wait-ms", type=int, default=12)
    parser.add_argument("--queue-size", type=int, default=256)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--threshold", type=float, default=0.45)
    parser.add_argument("--min-box-area", type=int, default=300)
    args = parser.parse_args()

    service = QueuedRealtimePlateService(
        detector_weights=args.detector,
        recognizer_weights=args.recognizer,
        detector_imgsz=args.imgsz,
        threshold=args.threshold,
        min_box_area=args.min_box_area,
        max_batch_size=args.batch_size,
        batch_wait_ms=args.batch_wait_ms,
        max_queue_size=args.queue_size,
    )
    started_at = time.perf_counter()
    server = ThreadingHTTPServer((args.host, args.port), make_handler(service, started_at))
    print(f"[plate-ai] ready on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        print("[plate-ai] shutting down")
        service.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
