$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$aiDir = Join-Path $root "ai\tst\Persian-License-Plate-Recognition"
$backendDir = Join-Path $root "backend"
$frontendDir = Join-Path $root "frontend"
$aiPython = Join-Path $aiDir "venv\Scripts\python.exe"
if ((Test-Path $aiPython)) {
  Push-Location $aiDir
  try {
    & $aiPython -c "import cv2" *> $null
    if ($LASTEXITCODE -ne 0) {
      $aiPython = "python"
    }
  } catch {
    $aiPython = "python"
  } finally {
    Pop-Location
  }
} else {
  $aiPython = "python"
}

Start-Process powershell -WorkingDirectory $aiDir -ArgumentList @(
  "-NoExit",
  "-Command",
  "& '$aiPython' plate_http_service.py --host 127.0.0.1 --port 8765 --imgsz 640 --threshold 0.45 --min-box-area 300"
)

Start-Process powershell -WorkingDirectory $backendDir -ArgumentList @(
  "-NoExit",
  "-Command",
  "python manage.py runserver 0.0.0.0:8000"
)

Start-Process powershell -WorkingDirectory $frontendDir -ArgumentList @(
  "-NoExit",
  "-Command",
  "npm run dev -- --host 0.0.0.0"
)

Write-Host "Started:"
Write-Host "  Plate AI: http://127.0.0.1:8765/health"
Write-Host "  Backend:  http://127.0.0.1:8000"
Write-Host "  Frontend: http://127.0.0.1:5173"
Write-Host ""
Write-Host "For phone live camera, open the site over HTTPS. Without HTTPS, use the in-page mobile camera/photo fallback."
