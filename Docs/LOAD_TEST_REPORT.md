# Load Test Report — 2026-08-25

Status: **NOT RUN / BLOCKED.** No staging target, credentials, traffic profile,
or telemetry endpoint was available. Consequently this report contains no
fabricated request rate, p95/p99, error rate, connection count, or SSE lag.

Required staging test: baseline HTTP traffic plus 20, 50, and 100 authenticated
SSE clients; reconnect bursts; concurrent user mutations; and Redis restart.
Record HTTP p50/p95/p99, 4xx/5xx, worker RSS/threads, MySQL connections/locks,
Redis errors, active streams, outbox growth, and event/reconcile lag. Pass/fail
thresholds must be agreed before execution.

`scripts/realtime_load.py` is ready for explicit staging use. It performs
read-only health load and optional authenticated SSE fanout; it does not issue
business mutations.
