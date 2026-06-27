$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.production.yml run --rm certbot `
  renew --webroot --webroot-path /var/www/certbot

docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.production.yml restart edge-nginx
