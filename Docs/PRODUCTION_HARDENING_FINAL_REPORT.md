# Production Hardening Final Report — 2026-08-25

## Code

- Backend hardening: transactional outbox, bounded replay, bounded retention,
  strict DB sessions, request IDs, liveness/readiness, migration drift fix.
- Frontend hardening: one shared SSE per tab, bounded dedupe, per-entity
  out-of-order suppression, automatic full-resync refresh, finite request
  deadlines, automatic idempotency keys for unsafe browser calls.
- Realtime: DB remains authoritative; Redis only signals after commit.
- Database: no new speculative index; local capacity and staging-data tooling
  are available.
- Infra: SSE Nginx settings remain route-specific; Docker logging rotates;
  optional ASGI canary path is added with WSGI preserved.
- Observability: request correlation and liveness/readiness implemented;
  dashboard/metrics backend requires platform integration.

## Tests

- Passed locally: Django check, migration drift check, 22 backend tests, 3
  frontend protocol tests, frontend production build, Compose validation, diff
  check, local capacity command.
- Failed: none in the final local verification.
- Blocked: real staging fault injection, browser heap/navigation soak,
  20/50/100 authenticated SSE fanout, representative large-data EXPLAIN,
  production backup verification, and actual production capacity measurements.

## Metrics

Local capacity tool only: MySQL `max_connections=151`, current connections 1,
conservative WSGI ceiling 72, reserve-adjusted ceiling 142, headroom 70. No
staging/production p95, p99, RPS, event lag, RSS, or DB peak was available.

## Production flags

Dark P0 deploy (first ~10 hours):

```env
LIVE_OUTBOX_ENABLED=false
LIVE_REPLAY_ENABLED=false
LIVE_V2_ENABLED=false
LIVE_ASGI_ENABLED=false
```

P1 after soak (2026-08-26). ASGI remains off:

```env
LIVE_OUTBOX_ENABLED=true
LIVE_REPLAY_ENABLED=true
LIVE_V2_ENABLED=true
VITE_LIVE_REPLAY_ENABLED=true
LIVE_ASGI_ENABLED=false
```

## Remaining blockers

P3 ASGI canary is still deferred. Activate Live V2 with
`scripts/enable_live_v2.ps1 -Apply` or `scripts/enable_live_v2.sh --apply`
against the production env file, then rebuild the frontend because
`VITE_LIVE_REPLAY_ENABLED` is a build-time flag.

## Final status

**P1 READY** — 10-hour dark soak elapsed; Live V2 flags may be turned on.
ASGI must stay false.
