# ASGI Compatibility Audit — 2026-08-25

Status: **development-complete; canary BLOCKED_EXTERNAL_ENV.**

| Area | Classification | Decision |
| --- | --- | --- |
| Django security/session/auth/CSRF middleware | Django sync middleware adapted by ASGI handler | Supported; retain current order. |
| CORS and messages middleware | Django-compatible sync middleware | Supported through Django adapter. |
| `IdempotencyMiddleware` | Synchronous DB-backed middleware | Keep synchronous; no async DB access is introduced. |
| `TenantLicenseLockMiddleware` | Synchronous business middleware | Keep synchronous; canary-test its protected routes. |
| ORM/business transactions | Synchronous Django ORM | Not rewritten; ASGI adapts sync views safely. |
| `StreamingHttpResponse` SSE generator | Sync iterator under Django ASGI | Canary-test fanout, disconnect, and graceful shutdown. |
| Redis relay thread | Process-local background thread with finite timeouts/backoff | Retain and validate restart behavior in staging. |

Implementation: `backend/asgi_gunicorn.conf.py` uses the maintained
`uvicorn_worker.GunicornWorker`. `backend/docker/entrypoint.sh` leaves the
existing WSGI command untouched unless `LIVE_ASGI_ENABLED=true` is explicitly
set. The rollback is setting that flag false and deploying the recorded WSGI
image/config.

Required external canary evidence: package image build, readiness/liveness,
authenticated SSE replay, Redis outage, worker graceful restart, middleware
route smoke tests, RSS/connection/latency comparison, and a rollback rehearsal.
