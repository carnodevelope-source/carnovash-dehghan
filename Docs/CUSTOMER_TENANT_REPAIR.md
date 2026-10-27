# Customer tenant isolation and historical repair

This change extends ca8a896 and 87cdd9c. It does not modify historical customer links in a
migration. Migration 0026 only creates the encrypted repair journal table.
Migration 0027 changes Django base-manager options only; it performs no table
rewrite or data repair and is reversible.
Never run migration, apply, recovery or rollback against production during review.

## Permanent protections

Customer resolution remains tenant-scoped with a unique (tenant, phone) database
constraint. Model clean/save, instance save_base and bulk_create validate customer ownership.
Instance writes lock the existing vehicle/customer in the write transaction.
Both the default and base managers use the protected QuerySet. Existing
customer and vehicle tenant ownership cannot be reassigned by save. QuerySet
update and bulk_update refuse tenant/customer fields, including expressions;
use a validated instance save for an operational customer change. Bulk upserts
are refused. Unrelated bulk updates keep their original behavior.

Explicit foreign customer/customer_id API input receives a generic validation
error. Historical invalid links still block ordinary edits and backups; the
application does not silently claim or copy a foreign customer.

This is an application ORM guarantee, not a database cross-table constraint.
Raw SQL, an explicitly constructed models.QuerySet, explicit Model.save_base(obj)
and external writers bypass it. Calling obj.save_base() is now protected.
Only the repair service and tests deliberately use that maintenance boundary.
The old backfill_tenants command cannot reassign these models through update;
NULL tenant records require separate human review, not this repair.

No trigger is installed. A production trigger would need separate MySQL 8.4
migration/restore and locking benchmarks, INSERT/UPDATE checks on both tables,
NULL semantics, and a rollout compatible with existing corrupt links. A normal
CHECK constraint cannot validate a different table. Current DB uniqueness and
FK constraints remain enabled. See [the DB enforcement assessment](CUSTOMER_TENANT_DB_ENFORCEMENT.md).
The absolute requirement covering arbitrary SQL is NOT satisfied by this release.

## Review and rehearsal (isolated staging only)

1. Take and verify an independent database backup. Use an isolated clone with
   no production SMS/payment credentials. Stop writers and scheduled jobs for
   planning/apply/rollback. The service fingerprints ALL fields in tenants,
   customers, vehicles, plate loyalty, vehicle jobs/lines/status history, wallets,
   payments, cashflow and wallet gateway requests, across tenants. Apply/rollback
   lock those rows and ranges. MySQL uses next-transaction REPEATABLE READ to
   block phantom inserts, including rows with NULL foreign keys. Session defaults
   are unchanged. MySQL repair must run outside any existing transaction. This is intentionally conservative and can be expensive;
   measure memory and lock duration on a staging clone. New MySQL child inserts
   wait on parent FK locks. External writers must also be stopped.
2. Apply reviewed schema changes only to the isolated database:
   `python manage.py migrate vehicles`.
3. Generate a dedicated Fernet key in a protected secret store using
   Fernet.generate_key(), without printing it or passing it in command arguments.
   Inject CUSTOMER_REPAIR_KEY directly into the maintenance process environment. Keep it
   separate from the backup key and retain it for journal audit/rollback. Do
   not commit it or paste it into logs. Restrict plan directory and DB access
   to the maintenance operator; Windows requires directory ACLs (mode 0600
   alone does not enforce Windows ACLs).
4. Preview without writing anything:
   `python manage.py repair_customer_tenant_links --dry-run --tenant 3`.
   Omit --tenant to inspect all tenants. No key is required for counts alone.
5. Export the encrypted proposal outside the repository:
   `python manage.py repair_customer_tenant_links --tenant 3 --plan /secure/repair.enc`.
   Files are exclusively created and never overwritten. The output is counts
   and a SHA-256 plan_hash, with no customer phone/name/plate. The encrypted
   version-2 plan contains phone data; its version-2 journal retains only
   affected original score fields, link IDs and fingerprints, not a full database
   copy. Old version-1 plans must be regenerated and reviewed.
6. Review the individual proposed actions without printing customer data:
   `python manage.py repair_customer_tenant_links --review-plan --plan /secure/repair.enc`.
   Review vehicle/tenant/customer IDs and kinds through authorized tenant
   records. Hash approval is operator attestation, not a separate user/role
   approval system. A person must explicitly approve the displayed exact hash.
7. Apply only that reviewed proposal:
   `python manage.py repair_customer_tenant_links --apply --plan /secure/repair.enc --approve-hash HASH`.
   Any change in the tracked customer/vehicle/financial/history tables aborts
   the entire transaction. Replaying an applied plan is explicitly refused. Modified
   proposals are recomputed and rejected. Invalid/empty/ambiguous mobile phones
   and NULL tenants are left untouched for human review. Supported phones are
   Iranian 09xxxxxxxxx, +98/0098 equivalents, and Persian/Arabic digits.
8. Run `python manage.py audit_customer_tenant_links` and
   `python manage.py diagnose_cloud_backup --tenant 3`. Remaining issues can
   involve unrelated relations and must be reviewed independently.

New customer profiles use only the owning vehicle's normalized phone and blank
optional identity fields; foreign profile identity is never copied. Profiles
are shared only inside the same tenant. No vehicle is deleted. Only affected
customers' yearly scores are rebuilt from their own tenant's noncancelled
visits. Existing payments, plate loyalty snapshots, SMS and vehicle signals are
not invoked by relinking. Foreign profile IDs remain, with their score rebuilt
using their own tenant visits only. The journal is encrypted in the transaction,
and is deliberately excluded from every tenant archive because it spans tenants.

## Conditional rollback

Keep the key and the returned run_id. With writers stopped, run:

`python manage.py repair_customer_tenant_links --rollback RUN_ID --approve-hash rollback:RUN_ID`

Rollback refuses subsequent changes in ANY of the tracked tables (including
new visits, payments, plate loyalty and historical jobs), a missing/wrong key,
legacy version-1 journals or a repeated rollback. Version-1 journals did not
fingerprint financial/history tables, so cannot prove absence of new activity;
keep them for manual review rather than forcing rollback.

Rollback atomically restores the approved previous customer links and original
existing customers' score values/timestamps. **No customer is deleted.** Every
profile created by repair retains all of its fields, score and timestamps.
The output contains restored_links, retained_customers and
unreferenced_customers (internal IDs only). An unreferenced profile is retained
for human review, including its existing score; there is no automatic cleanup.
The encrypted journal records this report and completion time in the same
transaction. A successful rollback deliberately does not reproduce the full
pre-repair database snapshot because the created profiles remain. Restoring the previous state intentionally restores the historical invalid
links: backups/ordinary edits will be blocked again. If subsequent activity has
occurred, perform human-reviewed forward repair instead; never force rollback.
The schema migration can be reversed, but doing so deletes the journal table;
do not reverse it until the encrypted audit records have been retained securely.

## Cloud backup sizing and validation

Tenant validation remains enabled. foreign_tenant_relation now reports only
schema model/field and a repair/manual-review hint. diagnose_cloud_backup
remains read-only. Its row/byte limit diagnostics are separate from relationship
errors; increasing limits cannot fix a foreign customer link.

Existing environment settings are configurable (defaults unchanged):

| Variable | Default | Meaning |
| --- | ---: | --- |
| CLOUD_BACKUP_MAX_ROWS | 20000 | Total fixture rows |
| CLOUD_BACKUP_MAX_JSON_BYTES | 16777216 | Uncompressed JSON budget |
| CLOUD_BACKUP_MAX_FIELD_BYTES | 1048576 | Individual field budget |
| CLOUD_BACKUP_MAX_FILES | 50000 | Media count |

Use diagnosis on a staging clone and allow measured growth/headroom. 300000 rows
and 268435456 JSON bytes are possible overrides, not recommended defaults. The
snapshot materializes Python objects and JSON so reserve substantially more RAM
than the JSON size; measure peak memory, free disk, transfer and restore time.
Set identical compatible limits for backup verification and isolated recovery.
Restart the relevant service after changing environment settings.

After repair, create/verify an encrypted staging backup and restore ONLY into
an isolated recovery database with recover_cloud_backup and its existing
--confirm-isolated-restore gate. Check customer/vehicle tenant equality, counts,
score values and absence of foreign customer identity in the recovered fixture.

## Tests

Local: run Django test labels for test_customer_tenant_isolation,
test_customer_tenant_repair, test_customer_tenant_migration and
apps.cloud_backup.tests with --settings=apps.cloud_backup.test_settings.

MySQL 8.4, isolated tmpfs with no production volumes or published ports:

`docker compose -p customer-repair-review -f docker-compose.cloud-backup-test.yml up --build --abort-on-container-exit --exit-code-from backup-tests`

The compose test command includes existing backup tests, the real concurrent
customer insert test, model/ORM protection, 137 synthetic bad links,
read-only preview, encryption, stale approval, ambiguity, atomic failure,
conditional rollback and backup/isolated restore after repair. It does not
connect to production. Shut down that explicitly named test project afterward.

## Validation for the follow-up (2026-10-27)

MySQL 8.4.11 tests use the dedicated customer-repair-final Compose project,
MySQL tmpfs storage, no published ports, and an unprivileged read-only runner.
The installed dependency image carvash-backup-isolated-test-backup-tests:latest
was reused with the current backend source mounted read-only at /app using a
temporary Compose override outside Git; no .env, keys or production data mounts
were changed. The checked-in Compose command with --build rebuilds the same
requirements and current source without this local cache optimization.

Final focused suite: **69/69 passed on MySQL 8.4.11**, with no skips, in
53.059 seconds. This includes row/range lock concurrency, simultaneous apply
(exactly one commit), concurrent customer registration, 137 mismatches distributed
132/1/4 over tenants 3/12/20, nondeleting rollback, financial/loyalty preservation,
read-only preview, replay/stale/tampered plans, and encrypted independent
backup/recovery. The explicit raw-SQL/custom-QuerySet bypass demonstration also
passes and is a documented limitation, not an enforced security invariant.

Synthetic 21,413-vehicle benchmark: planning 12.784 seconds under tracemalloc,
1,730,451 bytes peak traced Python allocation during planning, and 2.904 seconds
for the apply transaction including its locking scans, 137 relinks, score
rebuilds and encrypted journal write. These values exclude MySQL server memory
and are not production resource guarantees.

The supplementary broad Windows/SQLite run before the final MySQL-only range
lock test contained 128 tests: 119 passed, 4 failed, 5 MySQL checks skipped.
The four failures below are unchanged from the baseline; the new range-lock
test is covered by the successful final MySQL run. Migration drift and
whitespace checks passed. Migration 0027 is metadata-only; migration preservation
and the full latest schema were exercised in the MySQL suite.
The earlier broad SQLite run had four pre-existing failures, independently
reproduced from ca8a896 during the previous change:

- VehiclePlateLookupAutofillTests.test_lookup_resolves_letter_candidates_in_one_request
- VehicleStatusSmsTests.test_release_checkout_counts_facility_discount_once_from_list_price
- ReleasedSmsFixedDiscountTests.test_fixed_mode_writes_milestone_line
- ReleasedSmsFixedDiscountTests.test_step_mode_keeps_generic_percent

No existing tests were deleted or disabled. SQL/custom QuerySet bypass is a
passing boundary demonstration, not proof of SQL protection. These writes still
succeed without database enforcement; do not declare complete tenant isolation.
No production migration, repair, restore or data write was executed.

## Resource behavior

Fingerprinting uses primary-key pages of 500 full rows, including MySQL client
buffering. Planning retains only mismatches and candidate IDs matching their
phones. The journal retains affected scores and link IDs; it no longer copies
all visits/customers into an encrypted JSON snapshot. Memory still grows with
the number of mismatches/affected customers and the largest field in a page.
Fernet and JSON serialization materialize the plan/journal; they are not streaming
cipher formats. Do not treat the small synthetic benchmark as a production RAM
or latency guarantee.

Dry-run takes fingerprints before and after planning to detect concurrent changes.
Apply validates the approved fingerprint under locks and recomputes proposals.
Stop application/background/external writers for planning and maintenance anyway:
locking scans span the whole tracked database and can block unrelated tenants.
A database lock timeout/deadlock aborts the entire transaction; retry only after
checking/reviewing current state. There is no automatic repair retry.

Changed files in this follow-up:

- backend/apps/vehicles/models.py
- backend/apps/vehicles/tenant_protection.py
- backend/apps/vehicles/customer_tenant_repair.py
- backend/apps/vehicles/management/commands/repair_customer_tenant_links.py
- backend/apps/vehicles/migrations/0027_alter_customerprofile_options_and_more.py
- backend/apps/vehicles/tests/test_customer_tenant_repair.py
- Docs/CUSTOMER_TENANT_REPAIR.md
- Docs/CUSTOMER_TENANT_DB_ENFORCEMENT.md
