# Realtime & Performance Audit — 2026-08-25

Scope: `PRODUCTION_REALTIME_STABILITY_PLAYBOOK.md`, Sections 0–30. This is a
repository audit; no production host, metrics system, database backup, or
staging environment was accessed.

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
