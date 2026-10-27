# Customer tenant isolation and historical repair

This change extends ca8a896, 87cdd9c and fe7f079. It does not modify historical customer links in a
migration. Migration 0026 only creates the encrypted repair journal table.
Migration 0027 changes Django base-manager options only; it performs no table
rewrite or data repair and is reversible.
Never run migration, apply, recovery or rollback against production during review.

## Permanent protections

Django model/manager/serializer checks remain enabled. MySQL 8.4 additionally
uses the four guards from migration 0029: vehicle insert/update, customer
ownership/ID update and customer deletion protection. New foreign links are
rejected even through direct SQL/custom QuerySets. Existing invalid rows are
not rewritten by installation. See the implemented account/trigger model and
staged deployment/rollback instructions in
[CUSTOMER_TENANT_DB_ENFORCEMENT.md](CUSTOMER_TENANT_DB_ENFORCEMENT.md).

Migration 0028 creates the technical one-use authorization table; 0029 installs
its locked minimal definer and versioned triggers. They must be installed and
audited before maintenance. SQLite provides application protection only.

## Review and rehearsal (isolated staging only)

1. Take and verify an independent database backup. Use an isolated clone with
   no production SMS/payment credentials. Stop writers and scheduled jobs for
   planning/apply/rollback. The service fingerprints ALL fields in tenants,
   customers, vehicles, plate loyalty, vehicle jobs/lines/status history, wallets,
   payments, cashflow and wallet gateway requests, across tenants. Apply/rollback
   lock those rows and ranges using FOR SHARE (financial tables remain read-only to the
   maintenance account). A schema-specific advisory lock serializes maintenance
   transactions; it is not an authorization mechanism. MySQL uses next-transaction REPEATABLE READ to
   block phantom inserts, including rows with NULL foreign keys. Session defaults
   are unchanged. MySQL repair must run outside any existing transaction. This is intentionally conservative and can be expensive;
   measure memory and lock duration on a staging clone. RR full-range locks
   block new tracked rows, including NULL-FK rows. External writers must also
   be stopped.
2. Apply reviewed schema changes only to the isolated database:
   Follow the staged provisioning steps in the database-enforcement guide;
   migrate through 0029 and run check_customer_tenant_guards with
   --settings=apps.vehicles.provisioning_settings. Keep writers stopped.
3. Inject the separately provisioned CUSTOMER_REPAIR_DB_USER and
   CUSTOMER_REPAIR_DB_PASSWORD into this standalone process only, using a secret
   store. No web/restore process receives them. Generate a dedicated Fernet key in a protected secret store using
   Fernet.generate_key(), without printing it or passing it in command arguments.
   Inject CUSTOMER_REPAIR_KEY directly into the maintenance process environment. Keep it
   separate from the backup key and retain it for journal audit/rollback. Do
   not commit it or paste it into logs. Restrict plan directory and DB access
   to the maintenance operator; Windows requires directory ACLs (mode 0600
   alone does not enforce Windows ACLs).
4. Preview without writing anything:
   `python manage.py repair_customer_tenant_links --dry-run --tenant 3 --settings=apps.vehicles.maintenance_settings`.
   Omit --tenant to inspect all tenants. No key is required for counts alone.
5. Export the encrypted proposal outside the repository:
   `python manage.py repair_customer_tenant_links --tenant 3 --plan /secure/repair.enc --settings=apps.vehicles.maintenance_settings`.
   Files are exclusively created and never overwritten. The output is counts
   and a SHA-256 plan_hash, with no customer phone/name/plate. The encrypted
   version-2 plan contains phone data; its version-2 journal retains only
   affected original score fields, link IDs and fingerprints, not a full database
   copy. Old version-1 plans must be regenerated and reviewed.
6. Review the individual proposed actions without printing customer data:
   `python manage.py repair_customer_tenant_links --review-plan --plan /secure/repair.enc --settings=apps.vehicles.maintenance_settings`.
   Review vehicle/tenant/customer IDs and kinds through authorized tenant
   records. Hash approval is operator attestation, not a separate user/role
   approval system. A person must explicitly approve the displayed exact hash.
7. Apply only that reviewed proposal:
   `python manage.py repair_customer_tenant_links --apply --plan /secure/repair.enc --approve-hash HASH --settings=apps.vehicles.maintenance_settings`.
   Any change in the tracked customer/vehicle/financial/history tables aborts
   the entire transaction. Replaying an applied plan is explicitly refused. Modified
   proposals are recomputed and rejected. Invalid/empty/ambiguous mobile phones
   and NULL tenants or anomalous negative historical IDs are left untouched
   for human review rather than proposing a non-reversible repair. Supported phones are
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

`python manage.py repair_customer_tenant_links --rollback RUN_ID --approve-hash rollback:RUN_ID --settings=apps.vehicles.maintenance_settings`

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
transaction. Restoring each foreign historical link consumes an exact,
connection-bound, one-use authorization issued only by the restricted
maintenance account. The ordinary application cannot issue or reuse it. A successful rollback deliberately does not reproduce the full
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

## Validation for database enforcement (2026-10-27)

**Final MySQL 8.4.11 result: 95 passed, 0 failed, 0 skipped, in 99.880 seconds.**
The full focused Compose command includes existing cloud backup, customer
isolation, repair/concurrency, migration preservation and new SQL/account guard
tests. It verifies direct INSERT/UPDATE and custom-QuerySet rejection, actual
least-privilege app/maintenance/recovery logins, immutable owners/IDs, legacy
unrelated updates, single-use expired/tuple/connection-bound permissions,
ca8a896 historical-model compatibility, failed-rollback atomicity, migration
installation/retry/reversal/failure compensation, read-only audit and missing-
definer-grant recovery, and real isolated restore without a bypass capability.

The synthetic production-shaped repair preserved 137 visits distributed 132/1/4
across tenants 3/12/20, fixed only approved links and retained all new profiles
after rollback. Existing financial/loyalty histories are preserved and later
financial/history changes refuse rollback. No test was removed or disabled.

For 21,413 synthetic vehicle rows: planning took 10.877 seconds under tracemalloc,
peak traced Python planning allocation was 1,730,008 bytes, and apply's locking
transaction took 2.302 seconds. These measurements exclude MySQL server/native
memory and are not production performance/lock-duration guarantees.

Supplementary SQLite run before the last MySQL-only audit test: 94 tests,
63 passed and 31 MySQL-only checks skipped, no failures. SQLite intentionally
has no database guard guarantee. Migration drift and git whitespace checks
passed. Migrations/DDL/repair ran only on disposable test schemas. No Production
operation, real .env/key/password change or real-backup deletion occurred.
The test environment is a dedicated customer-guard-review Compose project,
MySQL 8.4.11 in tmpfs, no published ports or production data mounts, and a
read-only unprivileged runner. The cached dependency image is reused with the
current backend mounted read-only; the checked-in --build command includes all
current source and tests without depending on that local override.

All previous focused tests are retained. The previous broad vehicle suite had
four independently verified baseline failures (plate-letter lookup, facility
loyalty-discount expectation and two SMS SimpleTestCase DB-access failures).
Those unrelated tests have not been changed or disabled. MySQL guard integration
adds real ordinary/maintenance/restore credentials, raw SQL, explicit save_base,
custom QuerySets, permission denial, single-use expiry/connection/tuple checks,
concurrency, migration install/retry/reverse/failure compensation, and isolated
restore without maintenance capability.

## Resource behavior and limits

Fingerprinting uses primary-key pages of 500, including MySQL client buffering.
Planning retains mismatches and their candidate IDs; the journal stores only
affected scores and link IDs. Fernet/JSON still materialize the plan/journal,
so memory grows with mismatches/affected customers and field size. The synthetic
benchmark is not a production resource guarantee. Dry-run fingerprints before
and after planning; apply revalidates under RR shared row/range locks.

Keep external writers stopped during approved maintenance: scans cover every
tracked tenant, and long/large tables can block unrelated tenants. MySQL DDL
uses a five-second metadata-lock budget; maintenance uses a ten-second advisory
lock acquisition budget. DB lock timeout/deadlock aborts the whole transaction;
there is no automatic repair retry. Inspect state and re-review before retrying.
No production database, .env, password or real backup has been modified.

## Changed files

27 files changed in this task:

- Docs/CUSTOMER_TENANT_DB_ENFORCEMENT.md
- Docs/CUSTOMER_TENANT_REPAIR.md
- backend/apps/cloud_backup/snapshot.py
- backend/apps/cloud_backup/test_settings_mysql.py
- backend/apps/cloud_backup/tests.py
- backend/apps/vehicles/apps.py
- backend/apps/vehicles/customer_tenant_repair.py
- backend/apps/vehicles/db_checks.py
- backend/apps/vehicles/db_permissions.py
- backend/apps/vehicles/maintenance_settings.py
- backend/apps/vehicles/management/commands/check_customer_tenant_guards.py
- backend/apps/vehicles/management/commands/customer_tenant_grants.py
- backend/apps/vehicles/migrations/0028_customertenantauthorization.py
- backend/apps/vehicles/migrations/0029_mysql_customer_tenant_guards.py
- backend/apps/vehicles/models.py
- backend/apps/vehicles/mysql_guards.py
- backend/apps/vehicles/provisioning_settings.py
- backend/apps/vehicles/tests/guard_support.py
- backend/apps/vehicles/tests/mysql/__init__.py
- backend/apps/vehicles/tests/mysql/base.py
- backend/apps/vehicles/tests/mysql_runner.py
- backend/apps/vehicles/tests/test_customer_tenant_isolation.py
- backend/apps/vehicles/tests/test_customer_tenant_repair.py
- backend/apps/vehicles/tests/test_mysql_customer_guards.py
- backend/config/api.py
- backend/config/settings.py
- docker-compose.cloud-backup-test.yml
