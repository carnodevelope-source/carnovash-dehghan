#!/usr/bin/env sh
set -eu

# Purge all support tickets on production and verify HQ inbox visibility.
# Run on the Linux server from the project root:
#
#   chmod +x scripts/purge_and_verify_tickets.sh
#   ./scripts/purge_and_verify_tickets.sh
#
# Optional:
#   ./scripts/purge_and_verify_tickets.sh --keep   # only verify, do not delete
#   ./scripts/purge_and_verify_tickets.sh --no-sample

ENV_FILE="${ENV_FILE:-.env.production}"
COMPOSE="docker compose --env-file $ENV_FILE -f docker-compose.yml -f docker-compose.production.yml"
KEEP=0
CREATE_SAMPLE=1

for arg in "$@"; do
  case "$arg" in
    --keep) KEEP=1 ;;
    --no-sample) CREATE_SAMPLE=0 ;;
    *)
      echo "Unknown argument: $arg" >&2
      exit 1
      ;;
  esac
done

if [ ! -f "$ENV_FILE" ]; then
  echo "Missing $ENV_FILE" >&2
  exit 1
fi

echo "==> Ensuring backend container is running..."
$COMPOSE up -d backend

if [ "$KEEP" -eq 0 ]; then
  echo "==> Purging ALL support tickets on server DB..."
  $COMPOSE exec -T backend python manage.py purge_support_tickets --yes
else
  echo "==> Skipping purge (--keep)"
fi

echo "==> Verifying HQ ticket flow..."
if [ "$CREATE_SAMPLE" -eq 1 ]; then
  $COMPOSE exec -T backend python manage.py verify_hq_tickets --create-sample --amount 1000
else
  $COMPOSE exec -T backend python manage.py verify_hq_tickets
fi

echo ""
echo "Next checks in browser:"
echo "  1) Open https://carnowash.ir/hq  (or your domain)"
echo "  2) Go to مرکز تیکت"
echo "  3) Click بروزرسانی / filter برداشت/شارژ"
echo "  4) Open the sample ticket and confirm wallet action card is visible"
echo ""
echo "If ticket still missing after purge+sample, rebuild without cache:"
echo "  $COMPOSE build --no-cache backend frontend"
echo "  $COMPOSE up -d backend frontend edge-nginx"
