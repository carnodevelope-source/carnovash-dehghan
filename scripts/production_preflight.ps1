param(
    [Parameter(Mandatory = $true)][string]$EnvFile,
    [ValidateSet('dark', 'live-v2')][string]$Phase = 'dark'
)

$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $EnvFile)) { throw 'Env file not found.' }
$values = @{}
Get-Content -LiteralPath $EnvFile | ForEach-Object {
    if ($_ -match '^\s*([^#=]+)=(.*)$') { $values[$Matches[1].Trim()] = $Matches[2].Trim() }
}

function Assert-Flag {
    param([string]$Name, [string]$Expected)
    $actual = ''
    if ($values.Contains($Name)) { $actual = [string]$values[$Name] }
    $actual = $actual.ToLower()
    if ($actual -ne $Expected) { throw "$Name must be $Expected for phase $Phase (got '$actual')." }
}

if ($Phase -eq 'dark') {
    foreach ($key in 'LIVE_V2_ENABLED','LIVE_REPLAY_ENABLED','LIVE_OUTBOX_ENABLED','LIVE_ASGI_ENABLED') {
        Assert-Flag -Name $key -Expected 'false'
    }
    Write-Output 'PRODUCTION_PREFLIGHT_DARK_FLAGS=PASS'
    return
}

Assert-Flag -Name 'LIVE_OUTBOX_ENABLED' -Expected 'true'
Assert-Flag -Name 'LIVE_V2_ENABLED' -Expected 'true'
Assert-Flag -Name 'LIVE_REPLAY_ENABLED' -Expected 'true'
Assert-Flag -Name 'VITE_LIVE_REPLAY_ENABLED' -Expected 'true'
Assert-Flag -Name 'LIVE_ASGI_ENABLED' -Expected 'false'
Write-Output 'PRODUCTION_PREFLIGHT_LIVE_V2_FLAGS=PASS'
