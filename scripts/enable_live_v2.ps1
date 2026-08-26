param(
    [string]$EnvFile = '',
    [switch]$Apply
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

if (-not $EnvFile) {
    if (Test-Path -LiteralPath (Join-Path $repo '.env.production')) {
        $EnvFile = '.env.production'
    } else {
        throw 'Pass -EnvFile for the production Compose env (usually .env.production on the server).'
    }
}

$envPath = if ([System.IO.Path]::IsPathRooted($EnvFile)) { $EnvFile } else { Join-Path $repo $EnvFile }
if (-not (Test-Path -LiteralPath $envPath)) {
    throw "Env file not found: $envPath"
}

Copy-Item -LiteralPath $envPath -Destination "$envPath.bak-live-v2" -Force

function Set-EnvFlag {
    param([string]$Path, [string]$Name, [string]$Value)
    $lines = Get-Content -LiteralPath $Path
    $pattern = "^\s*$([regex]::Escape($Name))\s*="
    $replaced = $false
    $updated = foreach ($line in $lines) {
        if ($line -match $pattern) {
            $replaced = $true
            "$Name=$Value"
        } else {
            $line
        }
    }
    if (-not $replaced) {
        $updated = @($updated) + "$Name=$Value"
    }
    $utf8 = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllLines($Path, [string[]]$updated, $utf8)
}

# P1 after soak. ASGI stays off: that is a separate canary, not this step.
Set-EnvFlag -Path $envPath -Name 'LIVE_OUTBOX_ENABLED' -Value 'true'
Set-EnvFlag -Path $envPath -Name 'LIVE_V2_ENABLED' -Value 'true'
Set-EnvFlag -Path $envPath -Name 'LIVE_REPLAY_ENABLED' -Value 'true'
Set-EnvFlag -Path $envPath -Name 'VITE_LIVE_REPLAY_ENABLED' -Value 'true'
Set-EnvFlag -Path $envPath -Name 'LIVE_ASGI_ENABLED' -Value 'false'
Set-EnvFlag -Path $envPath -Name 'LIVE_REVISION_SAFETY_CHECK' -Value 'true'

Write-Output "Updated $EnvFile with Live V2 flags. LIVE_ASGI_ENABLED remains false."
Write-Output "Backup written to $EnvFile.bak-live-v2"

if (-not $Apply) {
    Write-Output 'Flags are written. Re-run with -Apply to recreate backend and rebuild frontend.'
    return
}

$composeArgs = @('--env-file', $envPath)
if (Test-Path -LiteralPath (Join-Path $repo 'docker-compose.production.yml')) {
    $composeArgs = $composeArgs + @('-f', 'docker-compose.yml', '-f', 'docker-compose.production.yml')
}
docker compose @composeArgs up -d backend
docker compose @composeArgs up -d --build frontend
Write-Output 'Live V2 apply complete. Verify /api/live/revision/ after login and a mutation from a second tab.'
