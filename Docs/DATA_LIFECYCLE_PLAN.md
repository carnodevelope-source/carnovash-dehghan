# Data Lifecycle Plan — 2026-08-25

Business data remains authoritative in MySQL and is not deleted by realtime
rollback. `LiveOutbox` is an additive replay aid with a configured 72-hour
retention default; `IdempotencyRecord` has a 168-hour default retention.

Status: **cleanup implementation not approved for production volume.** The
present command `prune_realtime_records` exists but deletes each eligible set
in one operation. Before scheduling it, replace this with an ordered,
bounded-batch job, test interruption/restart behavior, and record retention
volume and execution time in staging. Keep legal/business record retention
separate from these technical replay records.

## Update

The cleanup command now uses deterministic ordered ID selection, row locks,
short transactions, configured batch size, and a configured maximum batch
count for both technical tables. Staging must still measure duration and lock
behavior at volume before it is scheduled in production.
