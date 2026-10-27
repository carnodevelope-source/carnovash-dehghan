# Cloud Backup: server readiness and operator runbook

Opt-in scheduled encrypted tenant backups. Primary DB/media paths and application
services are unchanged. The preparation/deployment commands below are proposals;
none have been executed on production. The server layout was supplied by the
operator and must be rechecked before rollout.

## Supplied server topology

| Item | Location |
| --- | --- |
| Checkout | `/home/shivamouj/carvash-releases/source-master` |
| Active Compose | `docker-compose.yml` + `docker-compose.usb-local.yml` |
| Primary disk | ext4 `/dev/sda2` at `/mnt/server-data` |
| Docker root | `/mnt/server-data/docker` |
| DB | `carwash-db-1`, `carwash_carvash_mysql`, `/var/lib/mysql` |
| Media volume | `carwash_carvash_media`, server logical name `carvash_media` |
| Media host path | `/mnt/server-data/docker/volumes/carwash_carvash_media/_data` |
| Backend / frontend | `/app/media` / `/var/www/media` |
| Backup disk | ext4 `/dev/sdb1` at `/mnt/extra-storage` |
| UUID | `e8c44715-a4e9-45cc-b1cc-932e8e5e2db2` |
| Reviewed major:minor | `8:17`, recheck after reboot |
| Reported free space | About 434 GiB; measure again |

The server-local `docker-compose.usb-local.yml` is absent from this checkout.
Do not invent/replace it. Local config validation uses the explicitly marked
`backend/apps/cloud_backup/fixtures/server-compose.fixture.yml` representing the
supplied topology. Validate with the REAL server-local file before deployment.

The backup overlay's independent logical key `cloud_backup_media` has
`external: true`, explicit name `carwash_carvash_media`: it selects the existing
volume without project-prefix surprises or creation of an empty replacement.
It does not conflict with the server's logical `carvash_media` definition. Media
is RO/nocopy. The second disk root is RO; only its pre-existing `cloud-backups`
subdirectory is RW, only in the backup worker. Binds never create missing host
paths. No socket/devices/privileged mode; no ports; capabilities dropped,
no-new-privileges, read-only root, dedicated 10001:10001 identity, existing default
network and `db` dependency. Inspect the real server network configuration too.

## Contents, isolation and limits

`snapshot.py` explicitly classifies every first-party model. Unknown models,
even new tenant models, fail until reviewed. Include the tenant root, reviewed
tenant models, ticket messages/attachments, subscription periods/meters and only
referenced project/product/plan catalog rows. Reject cross-tenant FKs and shared
media paths. Nullable tenant-less HQ author references become null. Accounts with
`platform_role=hq_support` are platform identities even if assigned to a tenant:
exclude their private profiles from exports and null only optional references.
Nonnullable references still fail; ordinary cross-tenant relations remain blocked.

Include every owned FileField and AI image/sidecar. On Linux source components
are opened with directory FDs/O_NOFOLLOW; reject links/non-regular files. Capture
device/inode/size/mtime/ctime and compare when copying; also bind AI sidecar bytes
to their checked ownership using digests. Missing/replaced/changed files fail the
whole attempt. Unowned/orphan media and mixed AI JSONL logs are excluded; retain
per-image metadata. JSON business fields are data, not arbitrary file paths.

Exclude global runtime settings, sessions, auth memberships, replay/idempotency,
BackupRun history and HQ bulk-job orchestration. User hashes are encrypted, but
staff/superuser/platform roles and auth memberships are stripped. Re-provision
privileges after recovery. This is logical operational tenant recovery, not a
server image: platform configuration, external services and jobs need separate
disaster recovery setup. Preserve raw-fixture semantics in future model signals.

MySQL REPEATABLE READ uses no row/table locks; requires transactional InnoDB
business tables. Files are copied after the DB snapshot, so this is not a
simultaneous filesystem snapshot. Source changes can fail and retry an attempt.
No source DB/media writes occur.

Default caps: 20,000 total rows, 16 MiB fixture, 50,000 files, at most 1 MiB per
individual text/JSON field. Counts/field lengths are checked before unbounded
fetches; chunked ORM iteration, streaming media/encryption. Oversized tenants
fail with `snapshot_limit_exceeded`. These conservative caps reduce OOM risk
under 1 GiB; arbitrary nested JSON still requires staging memory measurements.
Raise limits only after sizing or implement a disk-backed streaming fixture.
There is no plaintext temporary archive.

`CLOUD_BACKUP_MAX_FIELD_BYTES` makes the individual field/sidecar cap configurable;
SQL measures UTF-8 byte length on both MySQL and SQLite. For a read-only report of
the first blocking limit, use `python manage.py diagnose_cloud_backup --tenant ID`.
It prints only schema labels and aggregate counts/bytes/limits, never field values,
paths, SQL or credentials, and creates neither BackupRun nor archive files.
Customer ownership and the approval-only historical repair plan are documented
in [CUSTOMER-TENANT-ISOLATION.md](CUSTOMER-TENANT-ISOLATION.md).

## Disk safety, scheduling and retention

`CLOUD_BACKUP_MOUNT=/mnt/extra-storage` is the filesystem mountpoint;
`CLOUD_BACKUP_ROOT=/mnt/extra-storage/cloud-backups` is the private destination.
The destination must already exist, mode 0700, owned by the effective worker UID.
Do not chown the disk root, DB or media. Runtime checks local mount/stat and host
mountinfo: reviewed major:minor, ext4 filesystem root, host RW, real mountpoint,
no symlink. UUID is checked by the read-only HOST preflight script; runtime has no
raw-device access. A changed major:minor fails closed until UUID is rechecked.

Root AND tenant directories are pinned using FDs. Writes cannot fall back to the
SSD directory underneath an unmounted filesystem. Each write checks mount/free
reserve. EIO, EROFS, ENOSPC and permissions get sanitized codes. Fully authenticate,
verify gzip/manifest/digests/FKs, atomically rename, then fsync. Failed transfers
preserve finalized backups. Encrypted stale partials are cleaned on the next
attempt under that tenant's flock. Existing old-layout `/mnt/extra-storage/tenant-*`
archives are not moved or deleted automatically.

Eligibility: active `CarWashFeaturePurchase.cloud_storage` only. The existing
purchase model has no expiry; installment locks do not revoke eligibility.
Six-hour success interval; poll each minute. Failure backoff grows from two
minutes to six hours. Recheck due status under the real filesystem flock; a
second worker cannot duplicate a scheduled successful run. Recover interrupted
run history when the next worker acquires its tenant lock.

Retention target 14, at least two, protect ALL versions younger than seven days.
**Seven-day protection takes precedence over 14:** at six-hour intervals about
28 young versions can coexist; a strict cap of 14 contradicts seven-day retention.
Prune only after a new verified success. Inactive/deleted tenants retain archives
indefinitely pending a separately approved policy. No subscription deletion hook.
Default free reserve 1 GiB. CLI reports disk free/total, mount state, stale success,
last attempt/success and last measured retained bytes. Configure operational
alerts separately. A second disk in the SAME server is not off-server backup.

## Encryption and key rotation

AES-256-GCM, HKDF-SHA256 per-archive key with random 256-bit salt, ordered 96-bit
nonce counters, authenticated final frame. New v2 headers contain an authenticated
nonsecret Key ID; v1 from commit `0a67d6a` remains readable. Verify every chunk,
gzip checksum/trailer, member digest, fixture ownership/FKs and encryption terminal.

Default single secret is a standard-Base64 32-byte key, private file permissions,
`/run/secrets/cloud_backup_key`; writer ID `primary`. Never use Django SECRET_KEY.
Optional `CLOUD_BACKUP_KEYRING_FILE` selects a private JSON map of Key ID -> Base64
key; `CLOUD_BACKUP_KEY_ID` selects the writer. Mount it with a separately reviewed
RO secret overlay, not environment key contents. Retain old IDs and keys.
`CLOUD_BACKUP_LEGACY_KEY_ID=legacy-v1` selects the original v1 key from the ring;
without a ring, v1 uses the single key file. Rotation requires old, new and any
legacy keys in the ring, followed by old/new restore tests BEFORE switching the
writer ID. Never overwrite the only old key copy. Keep offline key copies outside
the server/disk; losing keys makes archives unreadable. No actual keys in source.

## Proposed HOST preparation (not executed)

Confirm disk UUID/type/major:minor and persistent UUID mount configuration first:

```sh
findmnt -rn -M /mnt/extra-storage -o TARGET,SOURCE,FSTYPE,UUID,MAJ:MIN,OPTIONS
# Expected UUID e8c44715-a4e9-45cc-b1cc-932e8e5e2db2, ext4, reviewed 8:17.
# After approval, create ONLY the service directory; review any existing contents.
test ! -L /mnt/extra-storage/cloud-backups
sudo install -d -o 10001 -g 10001 -m 0700 /mnt/extra-storage/cloud-backups
```

New key preparation ONLY if no existing key is used; commands never print it:

```sh
sudo install -d -o root -g root -m 0700 /etc/carvash-backup
sudo sh -c 'test ! -e /etc/carvash-backup/primary.key && test ! -L /etc/carvash-backup/primary.key && set -C && umask 077 && openssl rand -base64 32 > /etc/carvash-backup/primary.key'
sudo chown 10001:10001 /etc/carvash-backup/primary.key
sudo chmod 0400 /etc/carvash-backup/primary.key
```

Compose file secrets use host permissions. Preserve an offline key copy through
the approved secret procedure. Never run generation over an existing key.
Inspect actual media read/traverse access as UID 10001. If denied, prepare a
narrowly scoped approved ACL/supplemental group for affected upload paths and
future uploads. Do not recursively chown media or make private files world-readable.
The source volume remains RO. Linux tests verify real 10001:10001 access.

Nonsecret variables: CLOUD_BACKUP_DEVICE=8:17, CLOUD_BACKUP_UID/GID=10001,
CLOUD_BACKUP_MEDIA_VOLUME=carwash_carvash_media, CLOUD_BACKUP_KEY_ID=primary,
CLOUD_BACKUP_KEY_HOST_FILE=/etc/carvash-backup/primary.key. Load private DB
credentials through the existing secure environment procedure, not source.

## Proposed MySQL account preparation (not executed)

Only table-level SELECT on reviewed snapshot tables/catalogs, and
SELECT/INSERT/UPDATE on `cloud_backup_backuprun`. No business writes/DELETE,
DDL, FILE, PROCESS, LOCK TABLES or administrative grants. REPEATABLE READ needs
no additional privileges. User auth M2M is excluded before serialization.

Generate the exact reviewable grants in development (no MySQL connection):

```sh
DB_ENGINE=sqlite python backend/manage.py cloud_backup_grants --database-name carwash --user carvash_backup --host '%' > /private/reviewed-backup-grants.sql
```

Authorized DBA account template, NOT executable with its placeholder password:

```sql
CREATE USER 'carvash_backup'@'%' IDENTIFIED BY '<PASSWORD_FROM_PRIVATE_SECRET_MANAGER>';
-- Review/apply the generated table-level grants, then:
SHOW GRANTS FOR 'carvash_backup'@'%';
```

Prefer a constrained Docker subnet host pattern when practical. No database-wide
ALL/SELECT, application writer reuse or password-bearing CLI/history. Integration
tests use only generated grants and prove source UPDATE, backup DELETE and DDL
are denied. No account/grant creation runs in the production worker.

## Proposed deployment and rollback (operator approval required)

The initial BackupRun migration is unchanged; no other app migrations. Apply only
through the approved migration workflow. The worker never auto-migrates.
Dedicated `Dockerfile.cloud-backup` pins the validated Python base digest and
Python dependencies in `cloud-backup-requirements.lock`; main backend build is
unchanged. For immutable releases retain the resulting backup image digest;
Debian apt repositories are not immutable snapshots.

Use the real server files and existing project name, after private settings load:

```sh
cd /home/shivamouj/carvash-releases/source-master
backup_compose() {
  docker compose -p carwash -f docker-compose.yml -f docker-compose.usb-local.yml \
    -f docker-compose.cloud-backup.yml --profile cloud-backup "$@"
}
export CLOUD_BACKUP_DEVICE=8:17
sh scripts/cloud-backup-preflight.sh
backup_compose config --quiet
```

Privately inspect resolved media volume/network; never paste full config with
credentials into chat. Both backend and backup must resolve to carwash_carvash_media.
After explicit approval AND migration/account prerequisites:

```sh
backup_compose build cloud-backup
backup_compose run --rm --no-deps cloud-backup check_cloud_backup
backup_compose up -d --no-deps --no-build cloud-backup
backup_compose exec cloud-backup python manage.py cloud_backup_status --tenant TENANT_ID
```

`check_cloud_backup` is read-only: mount, private destination, schema, key and
media-root access. It creates no backup. `--no-deps` prevents starting/recreating
primary services; MySQL must already be healthy. Do not use whole-project up,
down or down -v. Verify a first archive and isolated restore before acceptance.

Stop/rollback ONLY the worker; preserve archives, keys and BackupRun schema:

```sh
backup_compose stop cloud-backup
# Select a compatible reviewed prior image/digest; start ONLY cloud-backup
# using --no-deps --no-build. Do not reverse migration or delete volumes.
```

A v1-only worker cannot read v2 archives. Preserve a v2 recovery image/keyring
even if rolling the writer back.

## Isolated tests and recovery

SQLite (two disposable DBs):

```sh
DB_ENGINE=sqlite python backend/manage.py test apps.cloud_backup.tests --settings=apps.cloud_backup.test_settings --noinput
```

MySQL 8.4, separate test project, no production volumes/ports/services, tmpfs DB:

```sh
docker compose -p carvash-backup-isolated-test -f docker-compose.cloud-backup-test.yml up --build --abort-on-container-exit --exit-code-from backup-tests
# Cleanup only this explicitly named DISPOSABLE TEST project afterward.
```

Linux tests use root only in a PRIVATE mount namespace with new scratch ext4
loop images under `/tmp/carvash-backup-mount-test-*`, never the real backup disk:

```sh
cd backend
sudo env CLOUD_BACKUP_LINUX_MOUNT_TESTS=1 DB_ENGINE=sqlite CARWASH_INTERNAL_SCHEDULER=false \
  unshare --mount --propagation private /path/to/test-venv/bin/python manage.py test \
  apps.cloud_backup.tests_linux --settings=apps.cloud_backup.test_settings --noinput
```

Require unshare, mount/umount, mkfs.ext4 and loop support. Cover real effective
UID/GID, mount loss/identity, lazy-detach FD safety, interprocess flock, symlinks,
low space and RO filesystem. EIO/ENOSPC/transfer failure is injected in unit tests;
this does not emulate firmware faults. Never physically unplug production disks.

Recover only in an isolated environment with matching code/schema/key:

```sh
python manage.py recover_cloud_backup /private/source.cvb --tenant 123 --output /private/NEW-staging
```

Destination must be NEW, private and free of symlink parents. Authenticate before
any extraction; use the same opened regular archive for both passes. Failures may
leave private staging files, never overwrite live media. Decrypted fixture/media
are sensitive and must not be served. For DB restore define a separate migrated
empty recovery alias in private settings, allowlist it with
CLOUD_BACKUP_RECOVERY_ALIASES=recovery, and explicitly confirm:

```sh
python manage.py recover_cloud_backup /private/source.cvb --tenant 123 \
  --output /private/NEW-staging --database recovery --confirm-isolated-restore
```

Default/nonallowlisted aliases are refused. Recovery must have a distinct DB name
(SQLite paths normalized), no existing business rows or conflicting catalogs.
Raw loading is transactional, checks FKs and resets sequences. SQLite/MySQL drills
compare recovered record contents, relationships and media bytes. Do not point
recovery at ANY live DB; restrict its credentials independently. Final media
cutover, privileges/global service setup and actual production restore require
separate operator approval.
