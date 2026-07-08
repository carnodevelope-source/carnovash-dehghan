#!/usr/bin/env sh
set -eu

ENV_FILE="${ENV_FILE:-.env.production}"
COMPOSE="docker compose --env-file $ENV_FILE -f docker-compose.yml -f docker-compose.production.yml"

$COMPOSE run --rm certbot renew --webroot --webroot-path /var/www/certbot
$COMPOSE restart edge-nginx
