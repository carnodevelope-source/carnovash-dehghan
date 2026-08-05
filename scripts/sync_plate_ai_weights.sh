#!/usr/bin/env bash
set -euo pipefail

# Sync plate+color AI weights to a remote carvash checkout.
# Usage:
#   ./scripts/sync_plate_ai_weights.sh user@server:/var/www/carvash
#   ./scripts/sync_plate_ai_weights.sh user@server:/var/www/carvash --restart

if [ "${1:-}" = "" ]; then
  echo "Usage: $0 user@host:/path/to/carvash [--restart]"
  exit 1
fi

TARGET="$1"
RESTART="${2:-}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/ai/final/weights"
REQUIRED=(plate_detector.pt vehicle_detector.pt ocr_model.ts letter_model.ts color_model.ts)

for name in "${REQUIRED[@]}"; do
  if [ ! -f "$SRC/$name" ]; then
    echo "Missing local weight: $SRC/$name"
    exit 1
  fi
done

DEST="${TARGET%/}/ai/final/weights"
echo "Syncing weights -> $DEST"
rsync -avh --progress \
  --include='plate_detector.pt' \
  --include='vehicle_detector.pt' \
  --include='ocr_model.ts' \
  --include='ocr_model_cuda.ts' \
  --include='letter_model.ts' \
  --include='color_model.ts' \
  --include='README.md' \
  --exclude='*' \
  "$SRC/" "$DEST/"

if [ "$RESTART" = "--restart" ]; then
  ssh "${TARGET%%:*}" "cd '${TARGET#*:}' && docker compose --env-file .env.production up -d --build plate-ai"
fi

echo "Done."
