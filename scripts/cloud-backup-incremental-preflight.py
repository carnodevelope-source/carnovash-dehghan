#!/usr/bin/env python3
"""Read-only release gate. Never migrates, starts services or changes secrets."""
import argparse
import json
import os
import re
import subprocess
from pathlib import Path


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--revision',required=True)
    parser.add_argument('--backend-container',default='carwash-backend-1')
    parser.add_argument('--media-host-path',default=os.environ.get('CLOUD_BACKUP_LIVE_MEDIA_HOST_PATH'))
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    checks={}
    try:
        revision=subprocess.check_output(['git','rev-parse','--verify',args.revision+'^{commit}'],cwd=root,text=True).strip()
        image=subprocess.check_output(['docker','inspect',args.backend_container,'--format','{{.Config.Image}}'],text=True).strip()
        tag=image.rsplit(':',1)[-1]
        checks['deployed_revision_identified']=bool(re.fullmatch(r'[a-f0-9]{7,40}',tag))
        checks['no_downgrade']=checks['deployed_revision_identified'] and subprocess.run(
            ['git','merge-base','--is-ancestor',tag,revision],cwd=root,capture_output=True).returncode==0
        code="""import os,json
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
import django
django.setup()
from django.core.files.storage import default_storage
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute('SET TRANSACTION READ ONLY')
    cursor.execute('START TRANSACTION')
    try:
        cursor.execute('SHOW COLUMNS FROM cloud_backup_backuprun')
        fields={row[0] for row in cursor.fetchall()}
    finally:
        cursor.execute('ROLLBACK')
required={'backup_kind','base_run_id','parent_run_id','scheduled_for','retention_status','retention_error_code','retention_checked_at'}
from django.conf import settings
media=os.stat(settings.MEDIA_ROOT)
print(json.dumps({'media_identity':[media.st_dev,media.st_ino],'source_policy_deployed':default_storage.__class__.__module__=='config.media_storage',
    'backup_schema_ready':required<=fields,'missing_backup_columns':sorted(required-fields)}))
"""
        result=subprocess.run(['docker','exec','-e','CARWASH_INTERNAL_SCHEDULER=false',args.backend_container,
                               'python','-c',code],capture_output=True,text=True,check=True)
        backend=json.loads(result.stdout)
        identity=backend.pop('media_identity')
        checks.update(backend)
        if args.media_host_path:
            media=Path(args.media_host_path)
            info=media.stat()
            checks['media_binding_matches_live']=(media.absolute()==media.resolve()
                and [info.st_dev,info.st_ino]==identity)
        else:
            checks['media_binding_matches_live']=False
    except Exception:
        checks['preflight_error']=True
    ready=(checks.get('no_downgrade') and checks.get('source_policy_deployed')
           and checks.get('backup_schema_ready') and checks.get('media_binding_matches_live') and not checks.get('preflight_error'))
    print(json.dumps({'read_only':True,'ready_for_activation':bool(ready),'checks':checks},sort_keys=True))
    return 0 if ready else 1

if __name__=='__main__':
    raise SystemExit(main())
