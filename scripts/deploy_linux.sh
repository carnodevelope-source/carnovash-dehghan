#!/usr/bin/env sh
set -eu

ENV_FILE="${ENV_FILE:-.env.production}"

if [ ! -f "$ENV_FILE" ]; then
    echo "Missing $ENV_FILE. Create it from .env.production.example first." >&2
    exit 1
fi

ENV_PATH="$ENV_FILE"
case "$ENV_FILE" in
    */*) ;;
    *) ENV_PATH="./$ENV_FILE" ;;
esac

set -a
. "$ENV_PATH"
set +a

PRIMARY_DOMAIN="${PRIMARY_DOMAIN:-carnowash.ir}"
SECONDARY_DOMAIN="${SECONDARY_DOMAIN:-www.carnowash.ir}"
LETSENCRYPT_EMAIL="${LETSENCRYPT_EMAIL:-}"

if [ -z "$LETSENCRYPT_EMAIL" ]; then
    echo "LETSENCRYPT_EMAIL is required in $ENV_FILE for the first TLS certificate." >&2
    exit 1
fi

COMPOSE="docker compose --env-file $ENV_FILE -f docker-compose.yml -f docker-compose.production.yml"

echo "Building and starting production stack..."
$COMPOSE up -d --build

echo "Checking TLS certificate for $PRIMARY_DOMAIN..."
if $COMPOSE exec -T edge-nginx test -f "/etc/letsencrypt/live/$PRIMARY_DOMAIN/fullchain.pem"; then
    echo "TLS certificate already exists."
else
    echo "Requesting Let's Encrypt certificate..."
    $COMPOSE run --rm certbot certonly \
        --webroot \
        --webroot-path /var/www/certbot \
        --email "$LETSENCRYPT_EMAIL" \
        --agree-tos \
        --no-eff-email \
        -d "$PRIMARY_DOMAIN" \
        -d "$SECONDARY_DOMAIN"
fi

echo "Reloading edge nginx with HTTPS config..."
$COMPOSE restart edge-nginx

echo "Production stack is up."
$COMPOSE ps
