# Plate AI Runtime

This folder is the runtime used by the site for plate recognition.

The website does not call this folder directly from the browser. The flow is:

1. Frontend sends the captured image to Django at `/api/vehicles/plate-recognition/`
2. Django forwards the request to `PLATE_AI_SERVICE_URL`
3. `plate_http_service.py` runs detection + OCR and returns normalized plate data

## Health endpoint

```bash
http://127.0.0.1:8765/health
```

## HTTP endpoint

```bash
POST /recognize
Content-Type: application/json
```

Payload:

```json
{
  "session_id": "tenant-1:camera-1",
  "image_base64": "data:image/jpeg;base64,...",
  "timeout_sec": 4.5,
  "force_process": true
}
```

## Local development

Recommended launcher:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_dev_with_plate_ai.ps1
```

That script:

- starts `plate_http_service.py`
- waits for `/health`
- starts Django with `PLATE_AI_SERVICE_URL=http://127.0.0.1:8765`
- starts Vite

## Production runtime

Production is expected to run the same AI service through Docker Compose.
No nginx or frontend changes are needed for AI itself.
In the current Compose setup, `plate-ai` is part of the default stack and starts with the site.

Required env values:

```env
PLATE_AI_SERVICE_URL=http://plate-ai:8765
PLATE_AI_TIMEOUT_SECONDS=5
PLATE_AI_PORT=8765
PLATE_AI_IMGSZ=640
PLATE_AI_THRESHOLD=0.45
PLATE_AI_MIN_BOX_AREA=300
PLATE_AI_BATCH_SIZE=8
PLATE_AI_BATCH_WAIT_MS=12
PLATE_AI_QUEUE_SIZE=256
```

The Compose service uses the same runtime file:

```bash
python plate_http_service.py --host 0.0.0.0 --port 8765 --imgsz 640 --threshold 0.45 --min-box-area 300 --batch-size 8 --batch-wait-ms 12 --queue-size 256
```

## Runtime validation

Quick local check:

```bash
python check_runtime.py
```

Manual API check after startup:

```bash
curl http://127.0.0.1:8765/health
```

## Required files

These files must exist before deployment:

- `weigths/yolov8-detector/yolov8-s-license-plate-detector.pt`
- `weigths/dtrb-recoginzer/dtrb-None-VGG-BiLSTM-CTC-license-plate-recognizer.pth`
- `plate_http_service.py`
- `queued_realtime_plate_service.py`
- `light_plate_common.py`

If the AI service is down, Django returns `503` for plate recognition and the site continues working without changing the rest of production.
