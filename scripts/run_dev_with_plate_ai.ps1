$ErrorActionPreference = "Stop"

param(
  [string]$AiHost = "127.0.0.1",
  [int]$AiPort = 8765,
  [int]$BackendPort = 8000,
  [int]$FrontendPort = 5173,
  [int]$AiImageSize = 640,
  [double]$AiThreshold = 0.45,
  [int]$AiMinBoxArea = 300,
  [int]$AiBatchSize = 8,
  [int]$AiBatchWaitMs = 12,
  [int]$AiQueueSize = 256
)

$root = Split-Path -Parent $PSScriptRoot
$aiDir = Join-Path $root "ai"
$backendDir = Join-Path $root "backend"
$frontendDir = Join-Path $root "frontend"
$backendEntry = if (Test-Path (Join-Path $backendDir "manage_local.py")) { "manage_local.py" } else { "manage.py" }
$aiServiceUrl = "http://${AiHost}:${AiPort}"

function Resolve-PythonCommand {
  param([string]$WorkingDirectory)

  $venvPython = Join-Path $WorkingDirectory "venv\Scripts\python.exe"
  if (Test-Path $venvPython) {
    Push-Location $WorkingDirectory
    try {
      & $venvPython -c "import cv2" *> $null
      if ($LASTEXITCODE -eq 0) {
        return $venvPython
      }
    } catch {
    } finally {
      Pop-Location
    }
  }
  return "python"
}

function Wait-ForHttp {
  param(
    [string]$Url,
    [int]$TimeoutSeconds = 45
  )

  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  while ((Get-Date) -lt $deadline) {
    try {
      $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 4
      if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
        return $true
      }
    } catch {
      Start-Sleep -Milliseconds 700
    }
  }
  return $false
}

$aiPython = Resolve-PythonCommand -WorkingDirectory $aiDir
$backendPython = Resolve-PythonCommand -WorkingDirectory $backendDir

$env:PLATE_AI_SERVICE_URL = $aiServiceUrl
$env:PLATE_AI_TIMEOUT_SECONDS = "5"

$aiCommand = "& '$aiPython' plate_http_service.py --host $AiHost --port $AiPort --imgsz $AiImageSize --threshold $AiThreshold --min-box-area $AiMinBoxArea --batch-size $AiBatchSize --batch-wait-ms $AiBatchWaitMs --queue-size $AiQueueSize"
$backendCommand = "$env:PLATE_AI_SERVICE_URL='$aiServiceUrl'; $env:PLATE_AI_TIMEOUT_SECONDS='5'; & '$backendPython' $backendEntry runserver 0.0.0.0:$BackendPort"
$frontendCommand = "npm run dev -- --host 0.0.0.0 --port $FrontendPort"

Start-Process powershell -WorkingDirectory $aiDir -ArgumentList @(
  "-NoExit",
  "-Command",
  $aiCommand
)

if (-not (Wait-ForHttp -Url "$aiServiceUrl/health" -TimeoutSeconds 60)) {
  Write-Warning "Plate AI health endpoint did not become ready at $aiServiceUrl/health. Backend and frontend will still be started."
}

Start-Process powershell -WorkingDirectory $backendDir -ArgumentList @(
  "-NoExit",
  "-Command",
  $backendCommand
)

Start-Process powershell -WorkingDirectory $frontendDir -ArgumentList @(
  "-NoExit",
  "-Command",
  $frontendCommand
)

Write-Host "Started:"
Write-Host "  Plate AI: $aiServiceUrl/health"
Write-Host "  Backend:  http://127.0.0.1:$BackendPort"
Write-Host "  Frontend: http://127.0.0.1:$FrontendPort"
Write-Host ""
Write-Host "Backend was started with PLATE_AI_SERVICE_URL=$aiServiceUrl"
Write-Host "For phone live camera, open the site over HTTPS. Without HTTPS, use the in-page mobile camera/photo fallback."
