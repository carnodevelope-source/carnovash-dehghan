#!/usr/bin/env sh
set -eu

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$REPO_ROOT"

APPLY=0
ENV_FILE=""
for arg in "$@"; do
    case "$arg" in
        --apply) APPLY=1 ;;
        --env-file=*) ENV_FILE=${arg#--env-file=} ;;
        *) echo "Unknown argument: $arg" >&2; exit 1 ;;
    esac
done

if [ -z "$ENV_FILE" ]; then
    if [ -f .env.production ]; then
        ENV_FILE=.env.production
    else
        echo "Pass --env-file= for the production Compose env (usually .env.production on the server)." >&2
        exit 1
    fi
fi

if [ ! -f "$ENV_FILE" ]; then
    echo "Missing $ENV_FILE" >&2
    exit 1
fi

cp "$ENV_FILE" "$ENV_FILE.bak-live-v2"
set_flag() {
    name=$1
    value=$2
    if grep -q "^[[:space:]]*${name}=" "$ENV_FILE"; then
        tmp=$(mktemp)
        sed "s|^[[:space:]]*${name}=.*|${name}=${value}|" "$ENV_FILE" > "$tmp"
        mv "$tmp" "$ENV_FILE"
    else
        printf '%s=%s\n' "$name" "$value" >> "$ENV_FILE"
    fi
}

# P1 after soak. ASGI stays off: that is a separate canary, not this step.
set_flag LIVE_OUTBOX_ENABLED true
set_flag LIVE_V2_ENABLED true
set_flag LIVE_REPLAY_ENABLED true
set_flag VITE_LIVE_REPLAY_ENABLED true
set_flag LIVE_ASGI_ENABLED false
set_flag LIVE_REVISION_SAFETY_CHECK true

echo "Updated $ENV_FILE with Live V2 flags. LIVE_ASGI_ENABLED remains false."
echo "Backup written to $ENV_FILE.bak-live-v2"

if [ "$APPLY" -ne 1 ]; then
    echo "Flags are written. Re-run with --apply to recreate backend and rebuild frontend."
    exit 0
fi

COMPOSE="docker compose --env-file $ENV_FILE"
if [ -f docker-compose.production.yml ]; then
    COMPOSE="$COMPOSE -f docker-compose.yml -f docker-compose.production.yml"
fi

$COMPOSE up -d backend
$COMPOSE up -d --build frontend
echo "Live V2 apply complete. Verify /api/live/revision/ after login and a mutation from a second tab."
