#!/usr/bin/env sh
set -eu

# Fix HQ ticket visibility, purge stale tickets, and verify مرکز تیکت flow.
# Run on the Linux server from the project root:
#
#   chmod +x scripts/purge_and_verify_tickets.sh
#   ./scripts/purge_and_verify_tickets.sh
#
# Optional:
#   ./scripts/purge_and_verify_tickets.sh --keep
#   ./scripts/purge_and_verify_tickets.sh --no-sample
#   ./scripts/purge_and_verify_tickets.sh --keep-hidden   # do not auto-include hidden carwashes

ENV_FILE="${ENV_FILE:-.env.production}"
COMPOSE="docker compose --env-file $ENV_FILE -f docker-compose.yml -f docker-compose.production.yml"
KEEP=0
CREATE_SAMPLE=1
FIX_HIDDEN=1

for arg in "$@"; do
  case "$arg" in
    --keep) KEEP=1 ;;
    --no-sample) CREATE_SAMPLE=0 ;;
    --keep-hidden) FIX_HIDDEN=0 ;;
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

echo "==> Checking / fixing carwashes hidden from HQ (exclude_from_hq_reports)..."
$COMPOSE exec -T backend python manage.py fix_hq_tenant_visibility
if [ "$FIX_HIDDEN" -eq 1 ]; then
  # میلان and any other active carwash wrongly marked hidden will be included again.
  $COMPOSE exec -T backend python manage.py fix_hq_tenant_visibility --include-all-active --yes
fi

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
echo "  1) Open https://carnowash.ir/hq"
echo "  2) Go to مرکز تیکت and click بروزرسانی (Ctrl+F5)"
echo "  3) Open the sample ticket and confirm wallet action card is visible"
echo ""
echo "If still empty, rebuild images:"
echo "  $COMPOSE build --no-cache backend frontend && $COMPOSE up -d"
