"""Site-compatible HTTP bridge for the final plate + color models."""

import argparse
import base64
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import cv2
import numpy as np

from queued_realtime_plate_service import QueuedRealtimePlateService


def _decode_image(value: str):
    if not value: raise ValueError("image_base64 is required.")
    if "," in value and value.split(",", 1)[0].startswith("data:"): value = value.split(",", 1)[1]
    try: raw = base64.b64decode(value, validate=True)
    except Exception as exc: raise ValueError("image_base64 is not valid base64.") from exc
    frame = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
    if frame is None: raise ValueError("image payload is not a readable image.")
    return frame


def _as_bool(value):
    return value.strip().lower() in {"1", "true", "yes", "on"} if isinstance(value, str) else bool(value)


def _json(handler, code, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(code); handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body))); handler.end_headers(); handler.wfile.write(body)


def make_handler(service, started_at):
    class Handler(BaseHTTPRequestHandler):
        server_version = "CarWashPlateColorAI/2.0"

        def log_message(self, fmt, *args): print(f"[plate-color-ai] {self.address_string()} - {fmt % args}")

        def do_GET(self):
            if urlparse(self.path).path != "/health": return _json(self, 404, {"detail": "Not found."})
            _json(self, 200, {"ok": True, "uptime_sec": round(time.perf_counter() - started_at, 3), "metrics": service.get_metrics()})

        def do_POST(self):
            if urlparse(self.path).path != "/recognize": return _json(self, 404, {"detail": "Not found."})
            started = time.perf_counter()
            try:
                length = int(self.headers.get("Content-Length", "0") or "0")
                if length <= 0: raise ValueError("Request body is empty.")
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                session_id = str(payload.get("session_id") or "default").strip() or "default"
                decode_started = time.perf_counter()
                frame = _decode_image(str(payload.get("image_base64") or payload.get("image_data_url") or ""))
                decode_ms = (time.perf_counter() - decode_started) * 1000
                result = service.submit_frame(session_id, frame, float(payload.get("timeout_sec") or 4.0), _as_bool(payload.get("force_process", False)))
                result = dict(result); result["decode_latency_ms"] = round(decode_ms, 2); result["bridge_latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
                _json(self, 200, result)
            except (ValueError, json.JSONDecodeError) as exc: _json(self, 400, {"accepted": False, "detail": str(exc)})
            except Exception as exc: _json(self, 500, {"accepted": False, "detail": str(exc)})

    return Handler


def main():
    parser = argparse.ArgumentParser(description="Site-compatible queued plate + color AI service")
    parser.add_argument("--host", default="127.0.0.1"); parser.add_argument("--port", type=int, default=8765)
    # Kept for command-line compatibility with the old service; final uses bundled weights.
    parser.add_argument("--detector", default=None); parser.add_argument("--recognizer", default=None)
    parser.add_argument("--batch-size", type=int, default=8); parser.add_argument("--batch-wait-ms", type=int, default=12)
    parser.add_argument("--queue-size", type=int, default=256); parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--threshold", type=float, default=0.30); parser.add_argument("--min-box-area", type=int, default=300)
    parser.add_argument("--ocr-interval", type=int, default=12); parser.add_argument("--color-interval", type=int, default=18)
    args = parser.parse_args()
    service = QueuedRealtimePlateService(
        detector_imgsz=args.imgsz, threshold=args.threshold, min_box_area=args.min_box_area,
        max_batch_size=args.batch_size, batch_wait_ms=args.batch_wait_ms, max_queue_size=args.queue_size,
        ocr_interval=args.ocr_interval, color_interval=args.color_interval,
    )
    started = time.perf_counter(); server = ThreadingHTTPServer((args.host, args.port), make_handler(service, started))
    print(f"[plate-color-ai] ready on http://{args.host}:{args.port}")
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: print("[plate-color-ai] shutting down"); service.shutdown(); server.server_close()


if __name__ == "__main__": main()
