param(
    [Parameter(Mandatory = $true)][string]$BaseUrl
)

$ErrorActionPreference = 'Stop'
$base = $BaseUrl.TrimEnd('/')

# This script is intentionally read-only. Authenticated replay, mutation, and
# Redis-fault scenarios are exercised by the dedicated staging runbook only.
$live = Invoke-WebRequest -UseBasicParsing -Uri "$base/api/health/" -TimeoutSec 10
if ($live.StatusCode -ne 200) { throw "Liveness failed: $($live.StatusCode)" }
$ready = Invoke-WebRequest -UseBasicParsing -Uri "$base/api/health/ready/" -TimeoutSec 10
if ($ready.StatusCode -ne 200) { throw "Readiness failed: $($ready.StatusCode)" }
Write-Output 'STAGING_READ_ONLY_SMOKE=PASS'
