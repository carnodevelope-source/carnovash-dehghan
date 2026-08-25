# Production Rollout Checklist — Realtime V2

This checklist is ordered. Do not skip a failed gate and do not use it to make
an ASGI migration in one step.

## 0. Before deployment

- [ ] Verify a restorable MySQL backup.
- [ ] Record current container image IDs/tags and `.env.production` securely.
- [ ] Record p95/p99, 5xx, MySQL connections, worker RSS/threads, Redis errors,
      active SSE count and log-disk size.
- [ ] Calculate `workers × threads + scheduler + maintenance reserve` against
      MySQL `max_connections`; do not increase worker/thread values by guesswork.
- [ ] Resolve or explicitly quarantine the pre-existing `services` migration
      drift before a production migration run.

## P0 — safe code deployment

- [ ] Run the backend/frontend test commands in `REALTIME_PERFORMANCE_CHANGES.md`.
- [ ] Deploy code and apply migrations with all flags below false:

  ```env
  LIVE_V2_ENABLED=false
  LIVE_REPLAY_ENABLED=false
  LIVE_OUTBOX_ENABLED=false
  VITE_LIVE_REPLAY_ENABLED=false
  LIVE_ASGI_ENABLED=false
  ```

- [ ] Verify SSE heartbeat and `proxy_buffering off` only for
      `/api/live/events/`.
- [ ] Run navigation stress (100 mount/unmounts); confirm one EventSource per
      tab and no listener/timer growth.
- [ ] Run a slow vehicle creation and wallet action; confirm local disabling,
      no duplicate POST, no background full-screen overlay.
- [ ] Staging soak: repeat navigation/actions while measuring RSS, requests/min
      idle, DB connections and event lag at start and finish.

Rollback: keep flags off and redeploy the previously recorded image. This
requires no database rollback because the migration is additive and inactive.

## P1 — durable live replay (staging first)

- [ ] Run `apps.realtime.tests`; it verifies that all current signal producers
      use the feature-gated transactional boundary, that a rolled-back vehicle
      leaves neither business nor outbox data, and that outbox use outside an
      atomic boundary fails fast. Audit any newly introduced bulk producer
      separately because bulk ORM operations bypass signals.
- [ ] Enable `LIVE_OUTBOX_ENABLED=true` only; verify outbox rows and retention
      job (`python manage.py prune_realtime_records`) in staging.
- [ ] Enable `LIVE_V2_ENABLED=true`, `LIVE_REPLAY_ENABLED=true`, and build the
      frontend with `VITE_LIVE_REPLAY_ENABLED=true`.
- [ ] Client A mutation → Client B update without reload.
- [ ] Disconnect Client B → mutate A → reconnect B → missed events replay.
- [ ] Verify tenant A never receives tenant B event or sync row.
- [ ] Redis restart: business writes still succeed; reconnect reconciles.
- [ ] Same idempotency key/body replays once; changed body returns 409.

Rollback: set `LIVE_REPLAY_ENABLED=false`, `LIVE_V2_ENABLED=false`, then
`LIVE_OUTBOX_ENABLED=false` after observing no dependency. Keep the additive
rows for retention pruning; never delete business data to roll back realtime.

## P2 — growth controls

- [ ] Capture `EXPLAIN` for each new index/query before and after any migration.
- [ ] Keep query-budget and GET-no-write tests green with small/large datasets.
- [ ] Verify Docker json-file rotation after container recreation.
- [ ] Add actual HTTP/live/DB/process metrics before widening traffic.

## P3 — ASGI canary only after P0–P2 evidence

- [ ] Audit every middleware and sync dependency under `config.asgi`.
- [ ] Deploy an isolated staging endpoint/service using ASGI; do not replace
      the WSGI command globally.
- [ ] Perform SSE fanout, Redis outage and graceful restart soak tests.
- [ ] Canary a small traffic percentage; monitor p95, connection use, RSS,
      reconnects and error rate.
- [ ] Promote only after an agreed soak period; remove gthread legacy path only
      after successful rollback-tested canary.

Rollback: route traffic back to the WSGI image/config and set every V2/ASGI
flag false. Do not perform a destructive database rollback.

## Updated executable gates — 2026-08-25

- [ ] Run `scripts/production_verify.ps1` from the repository root.
- [ ] Apply additive `realtime.0001` and `services.0022`; record the image and
      confirm backup/restore evidence before production migration.
- [ ] Keep every V2 and ASGI flag false through the first staging deploy.
- [ ] Run `scripts/staging_verify.ps1 -BaseUrl <staging-url>`.
- [ ] Seed only an isolated staging tenant with
      `seed_realtime_staging_data --allow-staging`; never point it at
      production.
- [ ] Record `report_db_capacity --json` on the actual staging database.
- [ ] Run `scripts/realtime_load.py` at 20, 50, and 100 authenticated SSE
      clients and capture platform metrics; then run `realtime_soak.py`.
- [ ] Execute `redis_outage_verify.ps1 -AllowStagingRedisRestart` only against
      the staging Compose project and validate replay/reconcile.
- [ ] Enable flags independently only after the prior evidence passes:
      outbox → replay → V2. ASGI is a separate canary after its own audit.
