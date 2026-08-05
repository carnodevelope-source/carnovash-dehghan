$ErrorActionPreference = "Stop"

param(
  [Parameter(Mandatory = $true)]
  [string]$Target,
  [switch]$Restart
)

# Sync plate+color AI weights to a remote carvash checkout.
# Example:
#   .\scripts\sync_plate_ai_weights.ps1 user@server:/var/www/carvash
#   .\scripts\sync_plate_ai_weights.ps1 user@server:/var/www/carvash -Restart

$root = Split-Path -Parent $PSScriptRoot
$src = Join-Path $root "ai\final\weights"
$required = @(
  "plate_detector.pt",
  "vehicle_detector.pt",
  "ocr_model.ts",
  "letter_model.ts",
  "color_model.ts"
)

foreach ($name in $required) {
  $path = Join-Path $src $name
  if (-not (Test-Path $path)) {
    throw "Missing local weight: $path"
  }
}

if ($Target -notmatch "^[^:]+:.+") {
  throw "Target must look like user@host:/path/to/carvash"
}

$hostPart = $Target.Split(":")[0]
$pathPart = $Target.Substring($hostPart.Length + 1).TrimEnd("/")
$dest = "${hostPart}:${pathPart}/ai/final/weights"

Write-Host "Ensuring remote directory exists..."
ssh $hostPart "mkdir -p '$pathPart/ai/final/weights'"

$names = @(
  "plate_detector.pt",
  "vehicle_detector.pt",
  "ocr_model.ts",
  "ocr_model_cuda.ts",
  "letter_model.ts",
  "color_model.ts",
  "README.md"
) | Where-Object { Test-Path (Join-Path $src $_) }

Write-Host "Syncing weights -> $dest"
foreach ($name in $names) {
  Write-Host "  $name"
  scp (Join-Path $src $name) "$dest/"
}

if ($Restart) {
  ssh $hostPart "cd '$pathPart' && docker compose --env-file .env.production up -d --build plate-ai"
}

Write-Host "Done."
