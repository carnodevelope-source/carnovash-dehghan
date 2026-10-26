# Secondary tenant backups (opt-in, not deployed)

The primary database and media paths are unchanged. This is a scheduled logical
backup, not synchronous replication or a substitute for full disaster recovery.
Only `CarWashFeaturePurchase(feature_key='cloud_storage', is_active=True)` enables
new snapshots. The current purchase model has no expiry date; installment locks
do not revoke this eligibility. There is no subscription-triggered deletion.

## Contents and isolation

All first-party models with a tenant FK, plus ticket messages/attachments and
subscription periods/meters, are scoped to that tenant. Only referenced shared
project/product/plan catalog rows are included. New unclassified models cause an
error until their ownership is specified. Cross-tenant FKs and shared media paths
fail closed; optional references to tenant-less HQ authors become null. Tenant
user password hashes are encrypted in the archive, but staff/superuser/platform
roles and auth groups/permissions are intentionally cleared for recovery.

Session, replay/idempotency, backup history and HQ bulk-job orchestration records
are excluded. Global settings without a tenant are excluded. Existing JSON fields
are preserved as tenant business data, not interpreted as file references.
All currently declared FileFields are copied. AI audit image sidecars are checked
against both tenant ID and owned vehicle ID and copied with their images. Mixed
daily AI JSONL logs are not copied wholesale; per-image JSON metadata is retained.
Unknown/unreferenced files in MEDIA_ROOT cannot be assigned safely and are not
copied. Inventory future upload paths in this module when adding new storage.

The database export uses a repeatable-read transaction on MySQL (SQLite supported
for tests). File contents are copied afterward with size/mtime checks and SHA-256.
Concurrent deletion/change or missing files fail the snapshot and retry next tick.
This does not create a filesystem snapshot at the exact database transaction time.
Very large tenants require memory sizing: ORM records/fixture are currently held
in worker memory; media and encryption stream in bounded chunks. Worker memory is
limited by Compose and does not compete with web request workers without bounds.

## Storage and encryption

Destination: `/mnt/extra-storage/tenant-<numeric-id>/*.cvb`, directories 0700,
files 0600, dedicated Unix identity. No application-facing download API is added.
The mount must exist inside the container AND in the host mountinfo with the
configured Linux major:minor device. Bind mounting an unmounted host directory
does not pass this check. Writes resolve via an open mount directory FD, so an
unmount race cannot redirect writes into the SSD path under the mountpoint.
Each write checks the mount and free-space reserve. A disconnect/ENOSPC fails the
attempt, preserving previously finalized snapshots. Test physical detach on
staging before enabling production; unit tests simulate OS failure boundaries.

Encryption: random 256-bit external key; HKDF-SHA256 derives an archive-specific
AES-GCM key with a random 256-bit salt. Chunks use ordered nonce counters and an authenticated final frame.
No plaintext temporary archive. SHA-256 manifest of fixture and every file is
inside the encrypted archive. Full decrypt/checksum/FK verification is required
before atomic rename and fsync. `integrity_verified` means this check passed;
it does not claim an actual database restore drill has run for that snapshot.

Keep at least 14 versions by default, never fewer than two and never delete
versions newer than seven days. Pruning runs only after a successful new backup
for an eligible tenant. Inactive/deleted tenants' finalized archives remain
untouched indefinitely; removal requires a separate future retention policy.
Encrypted stale partials are cleaned on the next attempt under the tenant lock.
Filesystem flock prevents overlapping processes on the same disk. Backup history
uses a scalar tenant ID so tenant deletion cannot cascade-delete history.

## Host provisioning (requires separate deployment approval)

1. Verify primary data placement separately. This change does not migrate any
   data to the 3 TB disk or prove existing primary paths use it.
2. Mount the 500 GB filesystem persistently at `/mnt/extra-storage`. Record its
   UUID and `lsblk`/`findmnt` MAJ:MIN; set `CLOUD_BACKUP_DEVICE` to that MAJ:MIN.
   A changed device number after reboot blocks backups until reviewed/updated.
3. Provision UID/GID 10001 (or override both Compose variables), private writable
   backup root and read/traverse access to source media. Do not change ownership
   of existing application files indiscriminately. The source media mount is RO.
4. Generate a random 32-byte key encoded with standard Base64 into a private
   file OUTSIDE the repository and backup disk. Set `CLOUD_BACKUP_KEY_HOST_FILE`
   to its absolute path. Provision the secret file readable only by the backup
   UID (0400). Compose file secrets are bind mounts: host permissions matter.
   Keep an offline recovery copy; losing the key makes every archive unreadable.
   Do not replace the key while retaining old versions: archive/key rotation is
   not implemented yet. Never use Django SECRET_KEY as the encryption key.
5. Apply the new migration using the existing normal migration procedure.
   The backup worker overrides entrypoint so it never auto-migrates or starts
   web services. Provision a separate database account with SELECT on the app
   tables, and SELECT/INSERT/UPDATE only on `cloud_backup_backuprun`. No DELETE,
   DDL or write access to business tables. Set CLOUD_BACKUP_DB_USER/PASSWORD.
6. Compose overlay is opt-in:

   ```sh
   docker compose -f docker-compose.yml -f docker-compose.production.yml -f docker-compose.cloud-backup.yml --profile cloud-backup config --quiet
   # Only after deployment approval:
   docker compose -f docker-compose.yml -f docker-compose.production.yml -f docker-compose.cloud-backup.yml --profile cloud-backup up -d --build cloud-backup
   ```

No Docker socket, devices or privileged mode are exposed. The worker has no
published ports, drops capabilities, uses a read-only root, and reads host
mountinfo only. Default snapshot interval is six hours; worker polls every minute
and retries failed tenants. Enforce operational alerting for stale success / disk
reserve; a local second disk does not protect against loss of the whole server.

## Status and recovery

Operator command: `python manage.py cloud_backup_status --tenant <id>` returns
last attempt and last successful backup, integrity status, size, retained usage
at the last successful run and sanitized error codes. It exposes no client data.

Recovery is an administrative CLI, never a tenant-supplied path. Run in an
isolated environment with the same code/schema and key:

```sh
python manage.py recover_cloud_backup /private/source.cvb --tenant 123 --output /private/NEW-recovery-directory
```

The directory must not already exist. Archive is authenticated/validated before
plaintext extraction; files go under `media/`, data under `fixture.json`. Failure
can leave private staging files; inspect them manually, never serve that directory.
For actual DB recovery configure an explicit `recovery` DATABASES alias to a
separate, migrated empty database in a private settings module and add
`--database recovery`. Default DB restore is forbidden; existing tenants or
conflicting catalog rows abort recovery. Raw fixture loading preserves PK/FK
relationships, checks constraints and resets DB sequences. Business signals must
continue to honor Django's `raw` fixture semantics. Media remains in the private
staging directory until an operator validates and approves a separate cutover.
Re-provision privileges after recovery through normal administration.

## Validation

```sh
python manage.py test apps.cloud_backup.tests --settings=apps.cloud_backup.test_settings --noinput
```

Dedicated test settings use two disposable SQLite test databases. Tests exercise
tenant/media isolation, actual fixture recovery into the second database,
inactive eligibility, cross-tenant FKs, retention, authentication/tampering,
missing mount, disconnect, ENOSPC, retry and source-file errors. Linux mount/FD/
flock behavior and MySQL restore must additionally pass a staging drill before
production rollout. Never test disconnects against a disk containing live data.
