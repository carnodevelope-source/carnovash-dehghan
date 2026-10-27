"""Read-only audit compatible with the initial production BackupRun schema.

Does not migrate, create locks/directories, restore plaintext, reconcile history
or authorize deletion. Unknown/key-mismatched archives remain untouched.
"""
import hashlib
import os
import stat
from django.db import connection, transaction
from cryptography.exceptions import InvalidTag
from .archive import verify
from .models import BackupRun
from .snapshot import SnapshotError, fingerprint
from . import service


def audit_tenant(tenant_id):
    tenant_id = int(tenant_id)
    if tenant_id <= 0:
        raise SnapshotError('invalid_tenant')
    if connection.in_atomic_block:
        raise SnapshotError('nested_snapshot_transaction')
    if connection.vendor == 'mysql':
        with connection.cursor() as cursor:
            cursor.execute('SET TRANSACTION READ ONLY')
    with transaction.atomic():
        records = list(BackupRun.objects.filter(tenant_id=tenant_id).values(
            'id','archive_name','status','sha256','size_bytes','recovery_status'))
    successful = {row['archive_name']: row for row in records if row['status'] == 'success'
                  and row['recovery_status'] == 'integrity_verified'}
    files = []
    with service.pinned_root(writable=False) as root:
        folder = root / f'tenant-{tenant_id}'
        if not folder.exists():
            return {'tenant_id':tenant_id,'dry_run':True,'files':[],
                'successful_history':len(successful),'deletion_candidates':[],
                'deletion_authorized':False,'missing_registered_archives':sorted(successful)}
        with service.pinned_tenant(folder) as directory:
            for path in sorted(directory.glob('*.cvb')):
                item = {'archive_name':path.name,'registered_success':path.name in successful}
                try:
                    fd = os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
                    with os.fdopen(fd,'rb') as source:
                        info=os.fstat(source.fileno())
                        if (not stat.S_ISREG(info.st_mode) or info.st_nlink!=1
                                or info.st_uid!=os.geteuid() or stat.S_IMODE(info.st_mode)!=0o600):
                            raise SnapshotError('unsafe_archive')
                        digest=hashlib.sha256()
                        while block:=source.read(1024*1024):
                            digest.update(block)
                        source.seek(0)
                        verify(source,tenant_id)
                        if fingerprint(info)!=fingerprint(os.fstat(source.fileno())):
                            raise SnapshotError('source_changed')
                        item.update(integrity='verified',size_bytes=info.st_size,sha256=digest.hexdigest())
                        row=successful.get(path.name)
                        if row and (row['size_bytes']!=info.st_size or row['sha256']!=digest.hexdigest()):
                            item.update(integrity='failed',error_code='history_checksum_mismatch')
                except InvalidTag:
                    item.update(integrity='failed',error_code='authentication_failed_or_wrong_key')
                except Exception:
                    item.update(integrity='failed',error_code='archive_verification_failed')
                files.append(item)
            service.mount_guard()
    observed={item['archive_name'] for item in files}
    return {'tenant_id':tenant_id,'dry_run':True,'files':files,
        'successful_history':len(successful),'deletion_candidates':[],
        'deletion_authorized':False,'missing_registered_archives':sorted(set(successful)-observed)}
