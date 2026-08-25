# Production Rollback Plan — 2026-08-25

Status: **ready as a runbook; untested in staging.**

1. Stop rollout and preserve timestamps, request IDs, metrics, and logs.
2. Disable `LIVE_REPLAY_ENABLED` and `LIVE_V2_ENABLED`; then disable
   `LIVE_OUTBOX_ENABLED` after confirming no dependent code remains active.
   Keep `LIVE_ASGI_ENABLED=false`.
3. Rebuild the frontend with `VITE_LIVE_REPLAY_ENABLED=false` and redeploy the
   previously recorded healthy image/config if required.
4. Validate core login, vehicle, wallet, and normal polling/API paths; compare
   error rate, latency, MySQL sessions, and worker RSS with the pre-change
   baseline.
5. Do not delete or roll back business data. The realtime migration is
   additive; retain its technical rows for the normal retention cleanup path.

Before any production use, rehearse these steps on staging and record measured
recovery time and verification evidence.
