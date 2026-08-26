# Data Lifecycle Plan — 2026-08-25

Business data remains authoritative in MySQL and is not deleted by realtime
rollback. `LiveOutbox` is an additive replay aid with a configured 72-hour
retention default; `IdempotencyRecord` has a 168-hour default retention.

Status: **bounded cleanup is scheduled** on the internal background job cycle.
`prune_realtime_records` deletes only `LiveOutbox` and `IdempotencyRecord`
rows older than their retention windows. Business tables are never touched.

## Update

The cleanup command now uses deterministic ordered ID selection, row locks, short
transactions, configured batch size, and a configured maximum batch count.
The auth scheduler now calls it once per background cycle so enabling Live V2
cannot grow technical tables without a reclaimer. Legal/business record
retention stays separate from these replay/idempotency rows.
