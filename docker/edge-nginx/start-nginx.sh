#!/bin/sh
set -eu

PRIMARY_DOMAIN="${PRIMARY_DOMAIN:-carnowash.ir}"
SECONDARY_DOMAIN="${SECONDARY_DOMAIN:-www.carnowash.ir}"
CERT_PATH="/etc/letsencrypt/live/${PRIMARY_DOMAIN}/fullchain.pem"
KEY_PATH="/etc/letsencrypt/live/${PRIMARY_DOMAIN}/privkey.pem"

export PRIMARY_DOMAIN
export SECONDARY_DOMAIN

if [ -f "${CERT_PATH}" ] && [ -f "${KEY_PATH}" ]; then
    envsubst '${PRIMARY_DOMAIN} ${SECONDARY_DOMAIN}' \
        < /etc/nginx/templates/site-ssl.conf.template \
        > /etc/nginx/conf.d/default.conf
else
    envsubst '${PRIMARY_DOMAIN} ${SECONDARY_DOMAIN}' \
        < /etc/nginx/templates/site-http.conf.template \
        > /etc/nginx/conf.d/default.conf
fi

exec nginx -g 'daemon off;'
