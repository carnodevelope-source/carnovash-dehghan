# Database Scalability Audit — 2026-08-25

Status: **PARTIAL / BLOCKED.** This is a code-level audit only; no `EXPLAIN`,
table cardinality, slow-query log, lock telemetry, or production database was
read.

The additive realtime migration indexes `LiveOutbox` by `(tenant_id, id)` and
by `created_at`; replay/sync queries are tenant-scoped. Local query-budget
coverage exists for the vehicle list and passed as part of the 13-test suite.

Open blockers:

- SSE replay currently materializes an unbounded backlog.
- Retention deletion is not batch-bounded.
- The `services` app has unrelated migration drift.
- MariaDB reports strict SQL mode disabled.

Required next evidence is a staging dataset with representative growth,
`EXPLAIN` for replay/sync/list endpoints, connection/lock measurements, and
before/after query budgets. No new index is authorized by this audit.

## Update

Replay and cleanup blockers are fixed in code. `services.0022` resolves model
migration drift (its generated SQL is no-op), and Django connections now use
strict SQL mode. No staging `EXPLAIN`, cardinality, lock, or slow-query data
was available; index decisions remain evidence-gated.
