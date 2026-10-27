# MySQL customer ownership enforcement

This document supersedes the earlier design-only assessment. Migration **0028**
creates the technical authorization table; **0029** installs four MySQL 8.4
triggers and a locked, minimal definer account. Neither migration repairs,
rewrites, copies or deletes existing customer/vehicle records.

## Enforced invariant and NULL policy

For a new vehicle with customer_id, both tenant IDs must be non-NULL and equal,
and that customer must exist. An unassigned vehicle (customer_id NULL) and an
unassigned legacy customer (tenant_id NULL) may exist; they cannot be linked.

The vehicle UPDATE trigger rejects changes to its ID or tenant, and validates
any customer change. Unchanged legacy invalid links remain readable and allow
unrelated SQL updates. Moving an invalid link to a valid local customer or NULL
is allowed. Restoring an invalid link requires the exact exceptional permission
below. Customer UPDATE rejects ID/tenant changes, including NULL transitions;
phone, name and score changes are allowed. The fourth trigger rejects customer
DELETE, including REPLACE's delete phase, so profile history cannot disappear.
Use forward correction rather than ownership transfer or profile deletion.
Django's existing guards remain in place and are intentionally stricter about
ordinary edits of corrupt legacy rows until repair.

Validation locks the referenced customer with FOR SHARE. Customer ownership
and IDs are immutable, so concurrent raw SQL cannot move that customer after
validation. Guard failures use SQLSTATE 45000, errno 1644 and the fixed message
`Customer ownership validation failed.` No phone, name, plate or foreign tenant
value is returned. The existing API handler translates that exact error into a
controlled HTTP 400. Independent SQL statements, custom QuerySets, explicit
Model.save_base, bulk writes, foreign_key_checks=0 and session flags cannot
bypass these checks under the normal account.

The claim is relationship integrity under the installed triggers and restricted
accounts, not per-tenant row-level SELECT isolation for a shared DB credential.
A provisioning DBA remains a trusted administrator who can change schema/grants.
SQLite has application validation only; it is not a supported security rollout.

## Independent authorization, with no session-variable bypass

The normal application has NO access to either vehicles_customertenantauthorization
or vehicles_customertenantrepairrun, and no DDL, TRIGGER, EXECUTE, role grants or
GRANT OPTION. A separate maintenance login receives only:

- SELECT on the explicitly tracked tenant/customer/vehicle/financial/history tables;
- INSERT on CustomerProfile and UPDATE on score/year/timestamp columns only;
- UPDATE(customer_id) on VehicleEntry;
- SELECT/INSERT/UPDATE on the encrypted repair journal;
- SELECT/INSERT on the authorization table, with no UPDATE/DELETE.

The maintenance credential is a trusted authorization issuer, not an ordinary
application credential. It and CUSTOMER_REPAIR_KEY are available only in the
standalone approved maintenance process. The database validates issued exact
permissions; it does not decrypt the Fernet plan or independently verify human
approval. The Python issuer checks approval, decryption, fingerprints, state
and journal before issuing permissions. Manual issuance with maintenance/DBA
credentials is privileged activity and is outside the ordinary-account threat
model; those credentials must not be present in web or restore workers.

Apply needs no invalid-link exemption: it fixes links to valid local profiles.
Rollback checks the encrypted journal and the complete tracked-state fingerprint
inside the maintenance transaction. For each historical foreign link only, it
inserts an authorization bound to CONNECTION_ID(), vehicle ID, unchanged tenant,
exact old/new customer IDs, repair run ID, approved plan hash and five-minute
server-clock expiry. No session variable is consulted. The UPDATE trigger
locks and consumes that one row in the same transaction. Another connection,
wrong transition, expired row or consumed permission is rejected. An aborted
rollback rolls back both the link writes and permission issuance/consumption.
Audit rows are retained. No customer is deleted by rollback.

The trigger definer is named cw_guard_<schema-hash>@localhost. It is ACCOUNT LOCK,
with SELECT/TRIGGER on the two guarded tables and SELECT/UPDATE(consumed_at) on
the authorization table. It cannot log in, issue permissions, alter customer
ownership or read journal ciphertext. No privileged stored procedure is installed;
no account receives EXECUTE as part of this workflow.

MySQL triggers run in definer context; that context must not be mistaken for
the caller's identity. [MySQL stored-object security](https://dev.mysql.com/doc/refman/8.4/en/stored-objects-security.html)

## Process credentials and grant tooling

Provision fresh app, maintenance and isolated-restore accounts using your secret
manager/DBA workflow; tools never generate or print passwords. Do not add narrow
grants to root or an existing account with broad grants and call it restricted.

Generate reviewable SQL (no execution, no credentials):

```
python manage.py customer_tenant_grants --database-name SCHEMA --user APP_USER --host HOST --settings=apps.vehicles.provisioning_settings
python manage.py customer_tenant_grants --database-name SCHEMA --user MAINT_USER --host HOST --maintenance --settings=apps.vehicles.provisioning_settings
```

The output grants rights on specific tables only. Review and apply it with a
provisioning principal after the schema exists. The normal account excludes both
technical tables. Restore gets ordinary table grants in its isolated schema,
never maintenance grants. Cloud-backup's existing read-mostly grant generator
continues to exclude authorization/journal data.

Actual MySQL connections in normal config are checked for unsafe grants. A DBA,
role/wildcard/EXECUTE-bearing account, unreviewed view grants, or an account able to access maintenance
tables is rejected and its connection closed so it cannot be reused after an error. This check provides defense in depth; DB privileges and
triggers remain authoritative. The standalone provisioning_settings module
permits schema administration but grants no DB privileges itself. Never run a
web, backup or repair worker with that module.

For repair, explicitly use maintenance_settings. Inject CUSTOMER_REPAIR_DB_USER,
CUSTOMER_REPAIR_DB_PASSWORD and CUSTOMER_REPAIR_KEY from a protected store into
that process only; do not edit or commit real .env files. This module preserves
the target host/database configuration and changes only login credentials and
process role. It validates the actual account's narrow grants. A normal account
or DBA cannot be used as the repair account. No flag/session variable upgrades
an ordinary account's database permissions.

## Migration preflight, retry and reversal

0028 is an ordinary, small InnoDB technical-table migration. 0029 is non-atomic
because MySQL DDL commits independently of transaction.atomic(). The installer:

1. Serializes installers with a schema-specific GET_LOCK and a five-second
   metadata lock wait budget. This advisory lock is not authorization.
2. Checks MySQL 8.4 (not MariaDB), InnoDB engines, reviewed column types and
   customer/authorization indexes, configured app grants and provisioning access.
3. Rejects collisions/altered definitions in the reserved cw_customer_guard_v1_
   namespace, unreviewed BEFORE triggers on either table, an unlocked definer or
   unexpected definer privileges. It does not overwrite foreign definitions.
4. Creates the locked definer and its narrow grants, then missing triggers.
   Exact matching pre-existing guards are reused, so deployment retry is safe.
5. If an attempt fails, removes only triggers/account created by that attempt;
   business rows and pre-existing matching guards remain untouched. An interrupted
   reverse similarly reinstalls the guards it removed. A process/server crash
   can still leave a partial install; writers must stay stopped until retry and
   the read-only deployment audit succeed. Never fake the migration as applied.

A provisioning principal needs CREATE USER, the ability to assign the locked
DEFINER (SET_ANY_DEFINER or equivalent DBA capability), table-scoped privileges
and GRANT OPTION for the required grants, TRIGGER, metadata access for SHOW GRANTS
and the relevant mysql.user columns, plus normal Django schema-migration rights.
The persistent definer does not retain those provisioning privileges.

DDL does not scan or repair the 137 legacy rows. Trigger creation requires brief
metadata locks, so stop writers/long transactions first; a timeout is a failed
installation to inspect/retry, not grounds for raising the budget blindly.
Version-1 SQL definitions are immutable migration artifacts; future changes need
a versioned installer/migration, not edits to the v1 bodies.
[MySQL trigger DDL/security requirements](https://dev.mysql.com/doc/refman/8.4/en/create-trigger.html)

## Staged rollout from ca8a896 — operator approval required

No steps below have been executed on Production.

1. Verify an independent full DB backup and rehearse on an isolated clone. Inventory
   current grants, triggers, database engine and migrations (Production starts
   from vehicles.0025), and measure lock/latency impact on that clone.
2. Prepare new restricted runtime/maintenance accounts and an approved provisioning
   process. Inject the non-secret CUSTOMER_TENANT_GUARD_APP_ACCOUNT=user@host into
   migration/audit configuration; this names the actual intended runtime account.
   It may initially have USAGE only. Do not leave the runtime on root credentials.
3. Stop old web workers, schedulers and external writers. Install the new code
   without starting workers. With separately injected provisioning credentials:
   `python manage.py migrate vehicles 0028 --settings=apps.vehicles.provisioning_settings`.
   Apply/review the generated table grants; inventory any existing custom triggers.
   On an empty schema, complete migrations with the app account at USAGE first,
   then apply table grants and repeat the audit before any runtime startup.
4. Run `python manage.py migrate --settings=apps.vehicles.provisioning_settings`
   (including 0029), then
   `python manage.py check_customer_tenant_guards --settings=apps.vehicles.provisioning_settings`.
   The audit must report exactly four verified guards and restricted app grants.
   Confirm the runtime is actually configured for that account. New code rejects
   unsafe actual runtime credentials on connection creation.
5. While writers remain stopped, prepare/review the encrypted dry-run plan with
   maintenance_settings, approve its exact hash, and apply. The 137 supplied counts
   are only a reference; use current observed rows, never hardcoded production IDs.
   Invalid/ambiguous phones and NULL owners remain for human review.
6. Re-audit links, create/verify the staging tenant backup and restore into an
   independently migrated recovery schema under ordinary recovery credentials.
   Confirm zero foreign customer information and zero authorization/journal rows
   in each tenant archive. Only then approve runtime startup.

Triggers should be installed BEFORE approved repair: both apply and conditional
rollback operate with them active. There is no window of intentionally disabled
protection for repair. ca8a896's normal tenant-scoped registration remains valid
under the guard. Its raw invalid writes would fail at the database; its old API
handler lacks the new controlled-error adapter. An old binary is not allowed
back on broad credentials. Software rollback can retain 0028/0029 and restricted
runtime grants. Data rollback is a separate reviewed maintenance action that
uses the new tool, journal and credentials, never the old binary.

## Emergency procedure and portability

Keep writers stopped if installation or audit fails. Capture only schema/status
information; keep encrypted plans/journals and keys protected. Retry 0029 after
resolving the failed preflight/metadata lock. Exact partial definitions are
recognized. For an approved schema reversal only, migrate vehicles to 0028 using
the provisioning process; its tested reverse drops the four guards and locked
definer, retaining authorization and encrypted journal tables. DO NOT resume
ordinary writes without an alternative enforcement plan. Reapply 0029 and audit
before restarting. Do not reverse 0028/0026 or delete audit evidence as a cleanup
step. Neither reversing a trigger migration nor rolling back software restores
business data; only the separately approved conditional rollback does.

Physical/full logical DBA backups must preserve the trigger definitions,
authorization/journal records and locked definer/grants securely. Tenant archives
exclude all technical permission/audit records and keys. On a new server or
failover, provision/audit accounts and the schema-specific locked definer before
serving traffic; test replication/binlog privilege behavior for your topology.
An isolated restore schema gets its own migrated guards/definer based on its own
schema name. Set CUSTOMER_TENANT_GUARD_APP_ACCOUNT to that schema's
actual restore account when provisioning/auditing the recovery alias (use
--database=recovery with migrate). It must not name the live app account.
For a renamed destination schema, initialize it with migrations and restore
the validated fixture; do not blindly copy triggers with the source schema's
definer identity/grants. Restore never receives a bypass privilege. Do not use trigger-free
recovery output as a production schema.

## Executed validation

Final test results and the changed-file list are recorded in
[CUSTOMER_TENANT_REPAIR.md](CUSTOMER_TENANT_REPAIR.md). Tests use MySQL 8.4.11,
real ordinary/maintenance/restore logins with random in-memory credentials,
locked minimal definers and an isolated tmpfs DB. The test DBA handles migrations
and synthetic legacy fixtures only; all repair writes run as the restricted
maintenance account. Fixtures use exact audited one-use permissions, not disabled
guards. Disposable test teardown uses DBA-only TRUNCATE because customer DELETE
is forbidden; TRUNCATE does not disable/remove triggers, and the ordinary account
is explicitly tested unable to execute it. No test was removed to get a pass.
