#!/bin/sh
set -eu

python - <<'PY'
import os
import socket
import sys
import time

host = os.getenv("DB_HOST", "db")
port = int(os.getenv("DB_PORT", "3306"))
timeout = int(os.getenv("DB_WAIT_TIMEOUT", "90"))
deadline = time.time() + timeout

while time.time() < deadline:
    try:
        with socket.create_connection((host, port), timeout=3):
            print(f"Database is reachable at {host}:{port}")
            break
    except OSError:
        time.sleep(2)
else:
    print(f"Database did not become reachable at {host}:{port} within {timeout} seconds.", file=sys.stderr)
    sys.exit(1)
PY

python manage.py migrate --noinput
python manage.py collectstatic --noinput
# django_session only ever grows otherwise; expired rows are never reclaimed.
python manage.py clearsessions || true

if [ "${DJANGO_BOOTSTRAP_PRODUCTION_DATA:-True}" = "True" ]; then
    python manage.py seed_production_data
fi

exec "$@"
