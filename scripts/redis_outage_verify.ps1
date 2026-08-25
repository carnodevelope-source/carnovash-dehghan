param(
    [string]$ComposeFile = 'docker-compose.yml',
    [switch]$AllowStagingRedisRestart
)

$ErrorActionPreference = 'Stop'
if (-not $AllowStagingRedisRestart) {
    throw 'Refusing to restart Redis without -AllowStagingRedisRestart. Run only against the isolated staging Compose project.'
}
docker compose -f $ComposeFile stop redis
Write-Output 'Redis stopped. Execute authenticated business-write and reconnect checks now.'
docker compose -f $ComposeFile start redis
Write-Output 'Redis restarted. Verify outbox replay/reconcile and record metrics.'
