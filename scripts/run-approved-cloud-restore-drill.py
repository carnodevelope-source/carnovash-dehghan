#!/usr/bin/env python3
"""Restore approved real archives only to a new private MySQL network."""
import argparse
import datetime
import fcntl
import json
import os
from pathlib import Path
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
ART=Path('/mnt/extra-storage/carwash-rehearsal-artifacts/cloud-backup-release-f88169d')
NETWORK='carvash-cloud-restore-drill'
DATABASE='carvash-cloud-restore-db'


def exists(kind,name):
    return subprocess.run(['docker',kind,'inspect',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--tenants',nargs='+',type=int,required=True)
    parser.add_argument('--runtime',type=Path,default=ART/'worker-runtime.private.json')
    parser.add_argument('--image',default='carwash-backend:f88169d')
    args=parser.parse_args()
    if any(tenant<=0 for tenant in args.tenants):raise ValueError('invalid_tenant')
    art=args.runtime.parent
    lock=os.open(art/'restore-drill.lock',os.O_CREAT|os.O_RDWR,0o600)
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    code="""import os,json
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
import django
django.setup()
from apps.cloud_backup.chain_history import latest_chain
items=[]
for tenant in TENANTS:
    base,deltas=latest_chain(tenant)
    if base is None:raise ValueError('verified_base_required')
    items.append({'tenant':tenant,'run_id':deltas[-1].pk if deltas else base.pk,
        'full':{'name':base.archive_name,'sha256':base.sha256},
        'increments':[{'name':run.archive_name,'sha256':run.sha256} for run in deltas]})
print(json.dumps(items))
""".replace('TENANTS',repr(args.tenants))
    result=subprocess.run(['docker','exec','-e','CARWASH_INTERNAL_SCHEDULER=false','carwash-backend-1','python','-c',code],capture_output=True,text=True,check=True)
    targets=json.loads(result.stdout)
    config=json.loads(args.runtime.read_text())
    if config['services']['cloud-backup']['image']!=args.image:raise ValueError('restore_image_runtime_mismatch')
    key=config['secrets']['cloud_backup_key']['file']
    settings=config['services']['cloud-backup']['environment']
    if not exists('network',NETWORK):
        subprocess.run(['docker','network','create','--internal','--label','carvash.purpose=isolated-restore-drill',NETWORK],check=True,stdout=subprocess.DEVNULL)
    network=json.loads(subprocess.check_output(['docker','network','inspect',NETWORK],text=True))[0]
    if not network['Internal'] or network.get('Labels',{}).get('carvash.purpose')!='isolated-restore-drill':raise ValueError('private_network_required')
    if not exists('container',DATABASE):
        subprocess.run(['docker','run','-d','--name',DATABASE,'--label','carvash.purpose=isolated-restore-drill',
            '--network',NETWORK,'--network-alias','restore-db','--memory=2g','--memory-swap=2g','--cpus=1',
            '--tmpfs','/var/lib/mysql:rw,size=1g','-e','MYSQL_ALLOW_EMPTY_PASSWORD=yes','-e','MYSQL_ROOT_HOST=%',
            'mysql:8.4','--innodb-buffer-pool-size=128M','--mysqlx=0','--character-set-server=utf8mb4',
            '--collation-server=utf8mb4_unicode_ci','--sql-mode=STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION'],check=True,stdout=subprocess.DEVNULL)
    server=json.loads(subprocess.check_output(['docker','inspect',DATABASE],text=True))[0]
    if server['HostConfig']['PortBindings'] or server['Config']['Labels'].get('carvash.purpose')!='isolated-restore-drill':raise ValueError('unsafe_restore_server')
    if set(server['NetworkSettings']['Networks'])!={NETWORK}:raise ValueError('unsafe_restore_network')
    if not server['State']['Running']:
        subprocess.run(['docker','start',DATABASE],check=True,stdout=subprocess.DEVNULL)
    deadline=time.monotonic()+90
    while time.monotonic()<deadline:
        ready=subprocess.run(['docker','exec',DATABASE,'mysqladmin','ping','-h','127.0.0.1','--silent'],capture_output=True)
        if ready.returncode==0:break
        time.sleep(2)
    else:raise RuntimeError('restore_database_not_ready')
    env={'CARVASH_APPROVED_RESTORE_DRILL':'1','CARVASH_DRILL_TARGETS':json.dumps(targets),
        'CLOUD_BACKUP_TEST_MYSQL':'isolated','CLOUD_BACKUP_TEST_DB_HOST':'restore-db','DB_ENGINE':'sqlite',
        'CARWASH_INTERNAL_SCHEDULER':'false','LIVE_OUTBOX_ENABLED':'false','LIVE_V2_ENABLED':'false',
        'CLOUD_BACKUP_KEY_FILE':'/run/secrets/cloud_backup_key','CLOUD_BACKUP_KEY_ID':settings['CLOUD_BACKUP_KEY_ID'],
        'CLOUD_BACKUP_MAX_ROWS':settings['CLOUD_BACKUP_MAX_ROWS'],'CLOUD_BACKUP_MAX_JSON_BYTES':settings['CLOUD_BACKUP_MAX_JSON_BYTES'],
        'CLOUD_BACKUP_MAX_FIELD_BYTES':settings['CLOUD_BACKUP_MAX_FIELD_BYTES'],'PYTHONPATH':'/app'}
    command=['docker','run','--rm','--name','carvash-cloud-restore-validation','--network',NETWORK,'--read-only','--user','10001:10001',
        '--cap-drop','ALL','--security-opt','no-new-privileges','--memory=3g','--memory-swap=3g','--cpus=1','--shm-size=1g',
        '--tmpfs','/tmp:rw,mode=1777,size=256m','-w','/tmp',
        '--mount','type=bind,src='+str(ROOT/'backend')+',dst=/app,readonly',
        '--mount','type=bind,src=/mnt/extra-storage/cloud-backups,dst=/backups,readonly',
        '--mount','type=bind,src='+key+',dst=/run/secrets/cloud_backup_key,readonly']
    for name,value in env.items():command+=['-e',name+'='+str(value)]
    command+=['--entrypoint','python',args.image,'/app/manage.py','test','apps.cloud_backup.production_drill',
              '--settings=apps.cloud_backup.test_settings_mysql','--noinput','--verbosity','1']
    print('ISOLATED_RESTORE_STARTED '+json.dumps({'tenants':args.tenants,'production_database_not_connected':True}),flush=True)
    result=subprocess.run(command,capture_output=True,text=True)
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    report=art/('restore-drill-'+stamp+'.log')
    fd=os.open(report,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as output:output.write(result.stdout+'\n'+result.stderr)
    for line in result.stdout.splitlines():
        if line.startswith('RESTORE_RECEIPT '):print(line,flush=True)
    print('ISOLATED_RESTORE_EXIT '+str(result.returncode),flush=True)
    print('RESTORE_PRIVATE_LOG '+str(report),flush=True)
    if result.returncode:
        for line in result.stderr.splitlines():
            if 'isolated_restore_drill_failed:' in line:print(line,flush=True)
    raise SystemExit(result.returncode)

if __name__=='__main__':main()
