# Realtime & Performance Changes — 2026-08-25

No business calculation, API URL, UI content, or existing data was rewritten.
All new database behavior is gated and additive.

| Change | Files | Safety property |
| --- | --- | --- |
| Durable event cursor | `apps/realtime`, `apps/live.py` | `LiveOutbox` is a short-retention replay aid; MySQL business data remains authoritative. Event relay runs only through `transaction.on_commit`. |
| Replay/reconcile endpoints | `apps/live.py`, `config/urls.py` | `/api/live/sync/` and `/api/live/revision/` are authenticated, tenant-scoped, and return 404 while V2 replay is off. |
| One-tab reconnect state | `frontend/src/services/live.js` | Cursor is kept per browser tab; event IDs are deduplicated. Legacy hidden tabs are not disconnected, avoiding unrecoverable Pub/Sub loss. |
| Loading contract | `api.js`, `loading.store.js` | `navigation`/`blocking` may show the existing overlay; `background-sync` is silent; `mutation-user` exposes a local loading key. All requests have finite timeouts. |
| Idempotency | `apps/realtime/idempotency.py` | The same key + exact request replays JSON; same key + different body returns 409; competing in-progress request returns 409. |
| Critical mutation callers | vehicle store/dashboard, wallet panel | Local submit guards are retained and these operations add an `Idempotency-Key` plus a local loading key. |
| Configuration | env, compose, Gunicorn | Compose still defaults dark. Production example and `enable_live_v2` turn on outbox/V2/replay after soak; `LIVE_ASGI_ENABLED` stays false. |

## Database migration

`realtime.0001_initial` creates only:

- `LiveOutbox` with `(tenant_id, id)` and retention indexes;
- `IdempotencyRecord` with unique `(tenant_id, user, key)`.

It neither alters nor backfills existing business tables. Apply it through the
normal container migration path before enabling `LIVE_OUTBOX_ENABLED`.

## Verification completed locally

- `npm run build` — passed.
- `python manage.py test apps.realtime.tests apps.vehicles.tests.test_vehicle_list_query_budget --keepdb --verbosity 1` — 13 passed.
- `python manage.py check` — passed.
- `git diff --check` — passed.

The earlier strict-mode warning and `services` migration drift have since been
resolved by the hardened implementation update below.

## Hardened implementation update — 2026-08-25

- Bounded replay uses `LIVE_REPLAY_BATCH_SIZE`, `LIVE_REPLAY_MAX_EVENTS`, and
  `LIVE_REPLAY_MAX_AGE_HOURS`; unsafe cursors receive full-resync rather than a
  large replay.
- Cleanup is bounded for both `LiveOutbox` and `IdempotencyRecord`.
- Axios now sends an idempotency key for unsafe browser requests by default;
  ambiguous network/5xx retries retain the same key.
- WSGI remains default. An explicit optional ASGI canary path uses
  `uvicorn_worker.GunicornWorker` only when `LIVE_ASGI_ENABLED=true`.
- `scripts/production_verify.ps1` passed locally: 22 backend tests, 3 frontend
  protocol tests, build, checks, migration verification, capacity report,
  Compose validation, and diff check.

## P1 enablement after soak — 2026-08-26

- First SSE connections without `Last-Event-ID`/`after` skip outbox replay so
  enabling V2 cannot dump retained history onto every open tab.
- `prune_realtime_records` runs on the existing internal scheduler cycle.
- `scripts/enable_live_v2.ps1` / `scripts/enable_live_v2.sh` turn on outbox,
  V2, and replay, rebuild the frontend for `VITE_LIVE_REPLAY_ENABLED`, and
  leave `LIVE_ASGI_ENABLED=false`.
