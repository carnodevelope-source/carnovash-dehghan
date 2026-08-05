# Model weights (not committed — too large for git).
# Required files for plate-ai Docker / local service:
#   plate_detector.pt
#   vehicle_detector.pt
#   ocr_model.ts
#   letter_model.ts
#   color_model.ts
# Optional CUDA OCR:
#   ocr_model_cuda.ts
#
# Sync to server once, then docker compose will mount this folder:
#   scp -r ai/final/weights user@server:/path/to/carvash/ai/final/weights
#   # or: ./scripts/sync_plate_ai_weights.sh user@server:/path/to/carvash
