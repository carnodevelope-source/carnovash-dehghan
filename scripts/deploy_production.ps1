$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

Write-Host "Checking Docker engine..."
docker info | Out-Null

Write-Host "Building and starting application stack..."
docker compose --env-file .env.production up -d --build db backend plate-ai frontend

Write-Host "Starting edge Nginx on HTTP..."
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.production.yml up -d edge-nginx

Write-Host "Requesting Let's Encrypt certificate..."
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.production.yml run --rm certbot `
  certonly --webroot `
  --webroot-path /var/www/certbot `
  --email admin@carnowash.ir `
  --agree-tos `
  --no-eff-email `
  -d carnowash.ir `
  -d www.carnowash.ir

Write-Host "Reloading edge Nginx with TLS..."
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.production.yml restart edge-nginx

Write-Host "Final service status:"
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.production.yml ps
