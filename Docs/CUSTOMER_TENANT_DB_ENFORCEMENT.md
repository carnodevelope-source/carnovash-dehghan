# Database enforcement assessment — not installed

The current implementation is application-level protection. A test on MySQL
8.4.11 deliberately demonstrates that raw SQL and a separately constructed
models.QuerySet can still create foreign links or transfer customer ownership.
This test is evidence of a remaining gap. The absolute final acceptance criterion
against arbitrary SQL writers is therefore not met, even when all tests pass.

## Current write-path coverage

| Entry point | Result |
| --- | --- |
| Model.clean | Generic ownership validation; read-only, no write lock |
| Model.save / obj.save_base | Validate and write inside an atomic block; lock existing row and referenced customer |
| create / get_or_create insert | Goes through save; foreign customer rejected |
| get_or_create returning existing | No write; existing legacy row remains readable |
| update_or_create | Uses guarded save; ownership changes rejected |
| bulk_create | Validate within transaction; lock referenced customers; bulk conflict updates refused |
| bulk_update / QuerySet.update | Refuse tenant/customer fields, including expressions |
| default manager / _base_manager | Both use the protected QuerySet |
| API customer/customer_id | Foreign and nonexistent IDs receive the same generic error |
| Django explicit Model.save_base(obj), SQL, custom QuerySet | Bypass remains; not a database guarantee |
| Historical migration models | Historical schema semantics; no runtime manager/mixin injection |
| Approved repair relink/rollback | Deliberate maintenance bypass, under reviewed hash/journal, row/range locks and transaction |

The internal operational resolver remains the tenant-scoped implementation from
ca8a896. The reviewed operational registration/edit paths in vehicles serializers
use it; customer resolution is not broadened to other tenants. The historical
backfill_tenants command now refuses owner updates on these models. Backup
restoration uses Django's explicit Model.save_base only after the existing
archive tenant/relation validation and isolated-database checks. The repair
service is the only operational code constructing an unprotected vehicle
QuerySet. Fixtures deliberately use it to reproduce legacy corruption.

## Why this release adds no production trigger

This is an engineering risk decision, not a claim that MySQL cannot enforce the
relationship. MySQL supports BEFORE INSERT/UPDATE triggers and reports trigger
errors to the caller. A failed trigger statement on a transactional table rolls
back its changes. [MySQL 8.4 trigger semantics](https://dev.mysql.com/doc/refman/8.4/en/trigger-syntax.html)

A composite FK from vehicle(customer_id, tenant_id) to customer(id, tenant_id)
would reject the existing 137 mismatches when installed normally. NULL tenant
semantics would also need a separate policy. Installing constraints while
suppressing validation is not an acceptable fix. Immediate FK enforcement also
prevents rollback from restoring a historically invalid pair.
[MySQL FK behavior](https://dev.mysql.com/doc/refman/8.4/en/constraint-foreign-key.html)

Likewise, an unconditional vehicle trigger would reject the approved rollback's
historical pairs. A writable session-variable bypass would let the same SQL
writer disable the protection, so that design is rejected. An allowlist of all
historical invalid tuples would permit arbitrary SQL to recreate those tuples;
it is not a replacement for explicit approval.

## Proposed separately reviewed rollout

This design has not been implemented or validated as a production migration:

1. Separate ordinary application credentials from a short-lived maintenance
   account/procedure. The ordinary account must not have TRIGGER, DDL, permission
   management or write access to maintenance authorization/audit tables. Do not
   infer security from an application using a DB administrator account.
2. Install three schema-qualified, reversibly named triggers in a dedicated
   non-atomic MySQL-only migration: vehicle BEFORE INSERT, vehicle BEFORE UPDATE,
   customer BEFORE UPDATE. Installation must not rewrite or repair legacy rows.
3. Vehicle insert validates every non-NULL customer: its tenant must be non-NULL
   and equal to the referenced customer's tenant. A locking lookup of the
   customer must serialize against ownership changes. Vehicle update validates
   whenever customer_id/tenant_id changes, using NULL-safe comparisons. Unchanged
   legacy links remain readable and can receive unrelated historical updates.
4. Customer update refuses any ownership transfer, including NULL transitions,
   with a generic SQLSTATE error. Define how ID changes/deletions and privileged
   maintenance are handled; do not silently orphan or reassign histories.
5. Ordinary SQL and custom ORM writers then have the same DB checks. For approved
   rollback, provide a narrowly scoped definer procedure or independently
   privileged maintenance workflow that verifies an approved, locked run and
   restores only its exact prior links. It must not be callable/forgeable through
   normal application credentials. The current command is NOT yet that design.
6. Match trigger definer/privileges on deploy, failover, replication and isolated
   recovery; exercise install/uninstall and all existing flows on a production-
   shaped staging clone. Catch the selected SQLSTATE generically at API/service
   boundaries without exposing SQL or foreign customer data. Set a lock budget
   and verify indexed customer lookup cost under concurrent registration.

Trigger privilege checks use the definer context, so choosing the correct
maintenance authorization mechanism requires explicit privilege design rather
than trusting CURRENT_USER() to identify the invoking operator.
[MySQL CREATE TRIGGER security](https://dev.mysql.com/doc/refman/8.4/en/create-trigger.html)

After old links have been repaired and the historical rollback window is closed,
a reviewed composite FK rollout is another option. It would require an indexed
unique referenced key, explicit NULL policy, measured ALTER impact, a reversible
migration, and an agreed replacement for rollback that restores invalid links.

Until that rollout is reviewed and tested, do not represent arbitrary-SQL tenant
isolation as guaranteed or deploy this change as its final security sign-off.
The delivered rollback/data-preservation improvements are independently usable
in an isolated maintenance rehearsal.
