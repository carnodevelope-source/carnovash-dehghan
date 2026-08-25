# Production Observability Plan — 2026-08-25

Status: **design prerequisite; no dashboards or alerts were verified.**

Before a canary, expose and monitor: HTTP latency/error rate, SSE open streams,
reconnects and disconnects, replay/full-resync count, Redis publish/listener
errors, outbox backlog and cleanup duration, MySQL connections/locks/slow
queries, Gunicorn worker/thread saturation and RSS, plus container log-disk
use. Capture a baseline while every V2 flag remains off, then compare each
staged flag increment against it. Alert thresholds must be agreed from that
baseline, not guessed here.

`/api/health/` is liveness; `/api/health/ready/` performs a lightweight MySQL
`SELECT 1`. Redis is deliberately not a readiness dependency because it is not
the business source of truth. Dashboard/alert integration remains an external
infrastructure task.

Every response also carries `X-Request-ID`; a safe inbound value is preserved
or a new correlation ID is generated. Request payloads are not logged by this
middleware.
