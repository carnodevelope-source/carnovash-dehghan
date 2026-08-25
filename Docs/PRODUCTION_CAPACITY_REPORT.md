# Production Capacity Report — 2026-08-25

Status: **BLOCKED — no production or staging measurements were accessed.**

Known configured values are `GUNICORN_WORKERS=3`, `GUNICORN_THREADS=24`, and
`LIVE_MAX_SUBSCRIBERS=40` per worker. They are configuration defaults, not a
capacity finding. No `max_connections`, baseline MySQL sessions, scheduler
sessions, active SSE count, CPU/RSS, p95/p99, or event-lag values were
available; no number is inferred from them.

Before any V2 flag or worker setting changes, capture the database connection
budget and calculate the safe limit after reserving connections for MySQL,
maintenance, scheduler, migrations, and administrative access. Then establish
measured headroom with a staging SSE/load test. Do not change workers, threads,
or ASGI routing from this report.

## Local capacity-tool result

`python manage.py report_db_capacity --json` observed a local database with
151 max connections and one active connection. With 3 gthread workers × 24
threads and 9 reserved non-web connections, the tool calculates a conservative
web ceiling of 72, safe ceiling 142, and headroom 70 (46.36%). This is local
development evidence only; staging/production capacity remains
`BLOCKED_EXTERNAL_ENV`.
