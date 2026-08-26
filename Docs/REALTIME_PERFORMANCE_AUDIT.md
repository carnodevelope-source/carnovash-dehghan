# Realtime & Performance Audit — 2026-08-25

Scope: `PRODUCTION_REALTIME_STABILITY_PLAYBOOK.md`, Sections 0–30. This is a
repository audit; no production host, metrics system, database backup, or
staging environment was accessed.

## Current-state verification — 2026-08-25

**Decision: NO-GO for enabling V2 or deploying to production.** The safe code
path is present and dark by default, but staging/production evidence has not
been collected.

| Check | Evidence | Status |
| --- | --- | --- |
| V2/ASGI feature flags | `.env.production.example` sets `LIVE_V2_ENABLED`, `LIVE_REPLAY_ENABLED`, `LIVE_OUTBOX_ENABLED`, `LIVE_ASGI_ENABLED`, and `VITE_LIVE_REPLAY_ENABLED` to `false`; Compose defaults are also false. | PASS (dark) |
| Atomic outbox boundary | All 26 present signal producer models inherit `TransactionalLiveModelMixin`; `publish_live_event` refuses an outbox write outside `transaction.atomic()` and delivers only through `on_commit`. | PASS (local) |
| Local P1/P0 regression suite | `python manage.py test apps.realtime.tests apps.vehicles.tests.test_vehicle_list_query_budget --keepdb --verbosity 1`: 13 passed. | PASS (local) |
| Build/config validation | `npm run build`, `python manage.py check`, `makemigrations realtime --check --dry-run`, `docker compose --env-file .env.production.example config --quiet`, and `git diff --check` all passed. | PASS (local) |
| Staging fault/reconnect/soak/load evidence | No staging environment or measured telemetry was supplied or accessed. | BLOCKED |

### Verified release blockers

1. `_event_stream()` loads an unbounded replay list, while the HTTP sync
   endpoint is bounded. A large retained backlog could consume too much memory
   or hold an SSE worker for too long. Do not enable replay until a bounded
   paging/resync policy is implemented and tested.
2. `prune_realtime_records` performs one unbounded ORM delete per table. It
   needs a measured, bounded-batch cleanup strategy before retention runs at
   production volume.
3. Browser code deduplicates event IDs, but no browser integration test proves
   ordered application of out-of-order events or recovery of a detected gap.
4. Idempotency is opt-in at the HTTP client. It is used by the currently
   selected vehicle/wallet flows, but a complete inventory of payment,
   financial, and request-creating mutations has not been performed.
5. Current Gunicorn/SSE limits are static configuration, not a calculation
   against the actual MySQL connection budget and non-web consumers.
6. `makemigrations --check --dry-run` reports an unrelated pending `services`
   migration; MariaDB also reports strict SQL mode disabled. Both must be
   explicitly resolved or quarantined before a production migration gate.

## Baseline recorded before changes

| Area | Evidence | Result |
| --- | --- | --- |
| Frontend side effects | 265 lifecycle/listener/timer/watcher hits in `frontend/src` | Existing shared `services/live.js` already prevents more than one EventSource per tab. Views retain explicit unmount cleanup. |
| Backend realtime | `apps/live.py` uses `StreamingHttpResponse`, heartbeat, Redis relay and `transaction.on_commit` | Redis Pub/Sub was only a transient transport; there was no durable cursor/replay. |
| Query stability | Existing `test_vehicle_list_query_budget` | Vehicle list has a bounded-query and GET-no-write regression test. |
| Nginx and Docker | Dedicated `/api/live/events/` locations and compose log rotation | SSE buffering/cache/gzip are disabled only on the SSE route; json-file rotation exists. |
| Worker model | `backend/gunicorn.conf.py` | P0 remains gthread; ASGI is not enabled or deployed. |

Production values intentionally not invented: p95/p99, RSS, connection count,
Redis reconnects, CPU and log-disk baseline must be captured in staging and
production before each flag is enabled.

## Findings and disposition

1. The pre-existing frontend singleton fixes the per-component EventSource
   failure mode, but its hidden-tab disconnect could create a Pub/Sub gap.
   Hidden disconnect is now permitted only in a replay-enabled build.
2. Legacy events were UUID-only and not replayable. V2 adds a short-retention,
   tenant-scoped MySQL outbox; the DB stays the source of truth.
3. The old HTTP interceptor showed a global overlay by default. Requests now
   default to silent background mode; only explicit navigation/blocking mode
   opens the overlay, while loading keys are available for local controls.
4. Sensitive actions need server-side duplicate protection. The new middleware
   is header-driven and opt-in for legacy clients; same tenant/user/key/body
   replays the saved JSON response, while a changed body returns 409.
5. Publishers are Django model signals. All 26 current signal producer models
   now use the feature-gated `TransactionalLiveModelMixin`: it opens the
   transaction before `save()`/`delete()` emits the signal, so the business row
   and signal-created outbox row commit or roll back together. A fail-fast
   guard rejects an outbox write outside an atomic boundary. Bulk ORM methods
   intentionally do not emit signals; a future bulk producer must supply its
   own explicit transaction and outbox write.
6. `services` has a pre-existing unapplied model change (`0022...` proposed by
   `makemigrations --check`). It is unrelated and was deliberately not
   generated or included in this change.

## Required staged validation

The following cannot be honestly marked complete without a real staging stack:

- 100-route navigation listener/heap test;
- 20/50/100-client SSE fanout and burst test;
- Redis outage/reconnect and active-SSE graceful-restart test;
- database connection-capacity calculation against the actual MySQL
  `max_connections` and other worker consumers;
- ASGI middleware compatibility audit, canary, and soak test.

Those gates are executable checkboxes in `Docs/PRODUCTION_ROLLOUT_CHECKLIST.md`;
ASGI and V2 flags remain disabled by default.

## Hardened implementation update — 2026-08-25

- Replay is tenant-scoped, high-watermark bounded, batch streamed, and
  configured with maximum count/age limits. Invalid, future, expired, and
  over-limit cursors require an authoritative full resync.
- `prune_realtime_records` deletes only deterministic, row-locked batches for
  both short-retention tables.
- Browser protocol tests cover bounded dedupe and per-entity out-of-order
  suppression. A real navigation/heap soak remains external.
- `services.0022` clears migration drift as no-op SQL and strict SQL mode is
  applied per Django connection. `manage.py check` is clean locally.
- Local capacity tooling observed 151 max DB connections and calculated a
  conservative WSGI ceiling of 72 with reserve; it is not production evidence.

### Remaining external gates

Staging/production access is absent. Actual Redis restart, browser navigation
soak, 20/50/100 SSE fanout, large-data `EXPLAIN`, backup verification, and
production capacity measurements are `BLOCKED_EXTERNAL_ENV`, not passed by
inference.

## P1 enablement after soak — 2026-08-26

The dark P0 window (~10 hours) has elapsed. Live V2 may be turned on:

- `LIVE_OUTBOX_ENABLED=true`
- `LIVE_V2_ENABLED=true`
- `LIVE_REPLAY_ENABLED=true`
- `VITE_LIVE_REPLAY_ENABLED=true` (frontend rebuild required)

`LIVE_ASGI_ENABLED` stays `false`. Use `scripts/enable_live_v2.*`; rollback is
still flag-off, never a business-data rollback. A first SSE connection without
a cursor no longer replays retained outbox history.
