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
| Configuration | env, compose, Gunicorn | Flags default to safe/off; optional worker recycle values default to zero; no ASGI command was enabled. |

## Database migration

`realtime.0001_initial` creates only:

- `LiveOutbox` with `(tenant_id, id)` and retention indexes;
- `IdempotencyRecord` with unique `(tenant_id, user, key)`.

It neither alters nor backfills existing business tables. Apply it through the
normal container migration path before enabling `LIVE_OUTBOX_ENABLED`.

## Verification completed locally

- `npm run build` — passed.
- `python manage.py test apps.realtime.tests --keepdb --verbosity 2` — 5 passed.
- `python manage.py test apps.vehicles.tests.test_vehicle_list_query_budget --keepdb --verbosity 2` — 2 passed.
- `python manage.py check` — passed.
- `git diff --check` — passed.

The Django test runner reports an existing MariaDB strict-mode warning and the
unrelated `services` migration drift noted in the audit. Neither was changed.
