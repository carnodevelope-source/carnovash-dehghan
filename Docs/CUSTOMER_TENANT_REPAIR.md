# Customer tenant isolation and historical repair

This change extends ca8a896. It does not modify historical customer links in a
migration. Migration 0026 only creates the encrypted repair journal table.
Never run migration, apply, recovery or rollback against production during review.

## Permanent protections

Customer resolution remains tenant-scoped with a unique (tenant, phone) database
constraint. Model clean/save and bulk_create validate customer ownership. Existing
customer and vehicle tenant ownership cannot be reassigned by save. QuerySet
update and bulk_update refuse tenant/customer fields, including expressions;
use a validated instance save for an operational customer change. Bulk upserts
are refused. Unrelated bulk updates keep their original behavior.

Explicit foreign customer/customer_id API input receives a generic validation
error. Historical invalid links still block ordinary edits and backups; the
application does not silently claim or copy a foreign customer.

This is an application ORM guarantee, not a database cross-table constraint.
Raw SQL, save_base, unprotected base QuerySets and external writers bypass it.
Only the repair service and tests deliberately use that maintenance boundary.
The old backfill_tenants command cannot reassign these models through update;
NULL tenant records require separate human review, not this repair.

No trigger is installed. A production trigger would need separate MySQL 8.4
migration/restore and locking benchmarks, INSERT/UPDATE checks on both tables,
NULL semantics, and a rollout compatible with existing corrupt links. A normal
CHECK constraint cannot validate a different table. Current DB uniqueness and
FK constraints remain enabled.

## Review and rehearsal (isolated staging only)

1. Take and verify an independent database backup. Use an isolated clone with
   no production SMS/payment credentials. Stop writers and scheduled jobs for
   planning/apply/rollback. The service checks a fingerprint of ALL customer
   and vehicle fields, across tenants, and locks all tenant/customer/vehicle
   rows on apply. This is intentionally conservative and can be expensive;
   measure memory and lock duration on a staging clone. New MySQL child inserts
   wait on parent FK locks. External writers must also be stopped.
2. Apply reviewed schema changes only to the isolated database:
   `python manage.py migrate vehicles`.
3. Generate a dedicated Fernet key with
   `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
   Set CUSTOMER_REPAIR_KEY using a protected secret store/environment. Keep it
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
   plan contains phone data; its journal also contains before-state data.
6. Review the individual proposed actions without printing customer data:
   `python manage.py repair_customer_tenant_links --review-plan --plan /secure/repair.enc`.
   Review vehicle/tenant/customer IDs and kinds through authorized tenant
   records. Hash approval is operator attestation, not a separate user/role
   approval system. A person must explicitly approve the displayed exact hash.
7. Apply only that reviewed proposal:
   `python manage.py repair_customer_tenant_links --apply --plan /secure/repair.enc --approve-hash HASH`.
   Any changed customer/vehicle data aborts the entire transaction. Modified
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

Rollback refuses ANY subsequent customer/vehicle change (including new visits),
a missing/wrong key or a repeated rollback. It atomically restores the exact
previous customer links and affected score values/timestamps, and deletes only
profiles created by that run. It marks the retained encrypted journal rolled
back. Restoring the previous state intentionally restores the historical invalid
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

## Validation recorded for this change (2026-10-27)

On Windows/Python 3.13, with isolated SQLite default/recovery databases:
116 vehicle and cloud-backup tests ran: 110 passed, 4 failed, 2 skipped.
All new repair tests and backup/restore after repair passed. The two skipped
checks require MySQL (concurrent creation and restricted SQL account).
Docker's Linux engine pipe was unavailable, so MySQL 8.4 tests could not run
here. Run the isolated Compose suite before production rollout.

The same four failures were independently reproduced from an untouched git
archive of ca8a896, using the same interpreter and isolated test settings:

- VehiclePlateLookupAutofillTests.test_lookup_resolves_letter_candidates_in_one_request
- VehicleStatusSmsTests.test_release_checkout_counts_facility_discount_once_from_list_price
- ReleasedSmsFixedDiscountTests.test_fixed_mode_writes_milestone_line
- ReleasedSmsFixedDiscountTests.test_step_mode_keeps_generic_percent

These pre-existing failures were retained. Migration drift check and git diff
whitespace check passed. No production database, migration, backup or repair
command was used. Historical real-world mismatches still require reviewed
planning and apply after staging/MySQL validation.

Changed files:

- backend/apps/vehicles/models.py
- backend/apps/vehicles/tenant_protection.py
- backend/apps/vehicles/serializers.py
- backend/apps/vehicles/customer_tenant_repair.py
- backend/apps/vehicles/management/commands/repair_customer_tenant_links.py
- backend/apps/vehicles/migrations/0026_customertenantrepairrun.py
- backend/apps/vehicles/tests/test_customer_tenant_isolation.py
- backend/apps/vehicles/tests/test_customer_tenant_migration.py
- backend/apps/vehicles/tests/test_customer_tenant_repair.py
- backend/apps/cloud_backup/snapshot.py
- backend/apps/cloud_backup/tests.py
- docker-compose.cloud-backup-test.yml
- Docs/CUSTOMER_TENANT_REPAIR.md
