param(
    [Parameter(Mandatory = $true)][string]$EnvFile
)

$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $EnvFile)) { throw 'Env file not found.' }
$requiredOff = 'LIVE_V2_ENABLED','LIVE_REPLAY_ENABLED','LIVE_OUTBOX_ENABLED','LIVE_ASGI_ENABLED'
$values = @{}
Get-Content -LiteralPath $EnvFile | ForEach-Object {
    if ($_ -match '^\s*([^#=]+)=(.*)$') { $values[$Matches[1].Trim()] = $Matches[2].Trim() }
}
foreach ($key in $requiredOff) {
    if (($values[$key] ?? '').ToLower() -ne 'false') { throw "$key must be false before a fresh deployment." }
}
Write-Output 'PRODUCTION_PREFLIGHT_DARK_FLAGS=PASS'
