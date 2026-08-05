#!/bin/sh
set -eu

WEIGHTS_DIR="${PLATE_AI_WEIGHTS_DIR:-/app/weights}"
REQUIRED_WEIGHTS="plate_detector.pt vehicle_detector.pt ocr_model.ts letter_model.ts color_model.ts"

if [ ! -d "$WEIGHTS_DIR" ]; then
  echo "[plate-color-ai] weights directory missing: $WEIGHTS_DIR"
  echo "[plate-color-ai] copy ai/final/weights to the server, then rebuild/restart plate-ai."
  exit 1
fi

missing=0
for name in $REQUIRED_WEIGHTS; do
  if [ ! -f "$WEIGHTS_DIR/$name" ]; then
    echo "[plate-color-ai] missing weight: $WEIGHTS_DIR/$name"
    missing=1
  fi
done

if [ "$missing" -ne 0 ]; then
  echo "[plate-color-ai] required weights:"
  echo "  plate_detector.pt"
  echo "  vehicle_detector.pt"
  echo "  ocr_model.ts"
  echo "  letter_model.ts"
  echo "  color_model.ts"
  echo "optional: ocr_model_cuda.ts (faster on CUDA)"
  exit 1
fi

echo "[plate-color-ai] weights ok in $WEIGHTS_DIR"
exec "$@"
