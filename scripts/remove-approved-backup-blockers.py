#!/usr/bin/env python3
"""Exact user-approved stale attachment removal and reversible orphan isolation."""
import datetime,hashlib,json,os,subprocess
from pathlib import Path
ART=Path('/mnt/extra-storage/carwash-rehearsal-artifacts')
WORKER=ART/'cloud-backup-release-f88169d/worker-runtime.private.json'
CHECKPOINT=ART/'cloud-backup-checkpoint-20261028T090355Z.json'
manifest=json.loads(CHECKPOINT.read_text())
for row in manifest['receipts']:
    if not row['verified'] or row['plaintext_bytes']<=0:
        raise ValueError('checkpoint_verification_required')
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
export="""import os,json
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
import django;django.setup()
from apps.auth.models import SupportTicketAttachment
from django.core import serializers
obj=SupportTicketAttachment.objects.get(pk=5)
assert obj.ticket.tenant_id==12 and obj.ticket.status=='closed'
assert str(obj.created_at.date())=='2026-08-06'
assert not obj.file.storage.exists(obj.file.name)
assert not obj._meta.related_objects
print(serializers.serialize('json',[obj]))
"""
result=subprocess.run(['docker','exec','-e','CARWASH_INTERNAL_SCHEDULER=false','carwash-backend-1','python','-c',export],capture_output=True,text=True)
if result.returncode:raise RuntimeError('attachment_precondition_failed')
payload=result.stdout.strip().encode()
digest=hashlib.sha256(payload).hexdigest()
code="""import os,sys,io,json,hashlib,shutil
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
import django;django.setup()
from apps.cloud_backup import service
from apps.cloud_backup.archive import EncryptWriter,DecryptReader
from apps.cloud_backup.models import BackupRun
from apps.cloud_backup.chain_history import latest_chain,verify_chain_files
from pathlib import Path
for checkpoint_path,expected_hash in CHECKPOINT_ITEMS:
    assert service.archive_digest(Path(checkpoint_path))==expected_hash
payload=sys.stdin.buffer.read()
with service.pinned_root() as root:
    folder=root/'deployment-rollback'/('approved-cleanup-'+STAMP)
    folder.mkdir(mode=0o700)
    path=folder/'attachment-5.json.aesgcm'
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as target:
        writer=EncryptWriter(target,service.write_guard);writer.write(payload);writer.finish();target.flush();os.fsync(target.fileno())
    with path.open('rb') as source:
        checked=io.BufferedReader(DecryptReader(source)).read()
    assert hashlib.sha256(checked).digest()==hashlib.sha256(payload).digest()
    name='20261027T104429-798af5968dff42c3a6f39e8b7128380e.cvb'
    with service.locked_tenant(3) as directory:
        assert not BackupRun.objects.filter(archive_name=name).exists()
        base,deltas=latest_chain(3)
        assert base is not None
        verify_chain_files(directory,base,deltas,3)
        source=directory/name
        assert source.is_file() and not source.is_symlink() and source.stat().st_nlink==1
        before=service.archive_digest(source)
        destination=folder/'legacy-original.cvb.protected'
        fd=os.open(destination,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with source.open('rb') as old,os.fdopen(fd,'wb') as target:
            shutil.copyfileobj(old,target);target.flush();os.fsync(target.fileno())
        assert service.archive_digest(destination)==before
        service.sync_directory(folder)
        service.write_guard();source.unlink();service.sync_directory(directory)
    print(json.dumps({'encrypted_row_verified':True,'legacy_preserved_sha256':before,'legacy_removed_from_active':True,'rollback_directory':'/mnt/extra-storage/cloud-backups/deployment-rollback/approved-cleanup-'+STAMP}))
""".replace('STAMP',repr(stamp)).replace('CHECKPOINT_ITEMS',repr([(str(Path(manifest['directory'])/row['name']),row['encrypted_sha256']) for row in manifest['receipts']]))
result=subprocess.run(['docker','compose','-p','carwash','-f',str(WORKER),'run','-T','--rm','--no-deps','--entrypoint','python','cloud-backup','-c',code],input=payload,capture_output=True)
if result.returncode:raise RuntimeError('reversible_archive_cleanup_failed_without_attachment_deletion')
receipt=json.loads(result.stdout)
receipt.update(checkpoint=str(CHECKPOINT),attachment_sha256=digest,attachment_deleted=False)
journal=ART/('approved-cleanup-'+stamp+'.json')
fd=os.open(journal,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'w') as output:json.dump(receipt,output,indent=2);output.flush();os.fsync(output.fileno())
remove="""import os,json,hashlib
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
import django;django.setup()
from django.db import transaction
from django.core import serializers
from django.db.models.deletion import Collector
from apps.auth.models import SupportTicketAttachment
with transaction.atomic():
    obj=SupportTicketAttachment.objects.select_for_update().get(pk=5)
    assert obj.ticket.tenant_id==12 and obj.ticket.status=='closed'
    assert str(obj.created_at.date())=='2026-08-06'
    assert not obj.file.storage.exists(obj.file.name)
    raw=serializers.serialize('json',[obj]).encode()
    assert hashlib.sha256(raw).hexdigest()==DIGEST
    collector=Collector(using='default');collector.collect([obj])
    assert sum(len(v) for v in collector.data.values())==1 and not collector.fast_deletes
    count,details=obj.delete()
    assert count==1 and details=={'cw_auth.SupportTicketAttachment':1}
print(json.dumps({'attachment_deleted':True,'deleted_count':count,'ticket_preserved':True}))
""".replace('DIGEST',repr(digest))
result=subprocess.run(['docker','exec','-e','CARWASH_INTERNAL_SCHEDULER=false','carwash-backend-1','python','-c',remove],capture_output=True,text=True)
if result.returncode:raise RuntimeError('attachment_delete_failed_rollback_copy_preserved')
receipt.update(json.loads(result.stdout))
with journal.open('w') as output:json.dump(receipt,output,indent=2);output.flush();os.fsync(output.fileno())
print(json.dumps(receipt))
print('CLEANUP_JOURNAL '+str(journal))
