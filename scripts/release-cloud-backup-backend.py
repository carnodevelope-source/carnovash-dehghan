#!/usr/bin/env python3
"""Approved backend release with encrypted checkpoint and temporary routing.
No database restore/reset, no media movement and no dependency recreation.
Private rollback configuration stays outside Git with owner-only permissions.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
SOURCE=Path('/home/shivamouj/carvash-releases/source-master')
ART=Path('/mnt/extra-storage/carwash-rehearsal-artifacts')
BACKEND='carwash-backend-1'
FRONTEND='carwash-frontend-1'


def private_write(path,text):
    if path.exists():
        if path.read_text()!=text:raise ValueError('private_release_state_conflict')
        return
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as out:out.write(text);out.flush();os.fsync(out.fileno())


def inspect(name):
    return json.loads(subprocess.check_output(['docker','inspect',name],text=True))[0]


def run_env(arguments,env):
    if any('\n' in str(value) for value in env.values()):raise ValueError('unsupported_multiline_environment')
    fd=os.memfd_create('carvash-release-environment',0)
    try:
        os.write(fd,('\n'.join(key+'='+str(value) for key,value in env.items())+'\n').encode())
        os.lseek(fd,0,os.SEEK_SET)
        return subprocess.run(['docker','run',*arguments,'--env-file',f'/proc/self/fd/{fd}',
            '--entrypoint','python',IMAGE,'-u','-c',CODE],pass_fds=(fd,),capture_output=True,text=True)
    finally:os.close(fd)


def health(name,timeout=90):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        result=subprocess.run(['docker','exec',name,'python','-c',
            "from urllib.request import urlopen; print(urlopen('http://127.0.0.1:8000/api/health/',timeout=4).status)"],capture_output=True,text=True)
        if result.returncode==0 and result.stdout.strip()=='200':return True
        time.sleep(2)
    return False


def route(text):
    result=subprocess.run(['docker','exec','-i',FRONTEND,'sh','-c',
        'cat > /etc/nginx/conf.d/default.conf && nginx -t && nginx -s reload'],input=text,capture_output=True,text=True)
    if result.returncode:raise RuntimeError('frontend_route_validation_failed')


def override(image,env,command,mounts):
    escaped={key:str(value).replace('$','$$') for key,value in env.items()}
    volumes=[]
    for item in mounts:
        if item['Type']!='bind':raise ValueError('unexpected_backend_mount')
        volumes.append({'type':'bind','source':item['Source'],'target':item['Destination'],
            'read_only':not item['RW'],'bind':{'create_host_path':False}})
    return ('services:\n  backend:\n    image: '+image+'\n    build: !reset null\n    entrypoint: []\n'
        +'    command: '+json.dumps(command)+'\n    environment: !override '+json.dumps(escaped)+'\n'
        +'    volumes: !override '+json.dumps(volumes)+'\n')


def compose(path):
    cmd=['docker','compose','-p','carwash']
    if (SOURCE/'.env').is_file():cmd+=['--env-file',str(SOURCE/'.env')]
    return cmd+['-f',str(SOURCE/'docker-compose.yml'),'-f',str(path)]


def main():
    global IMAGE,CODE
    parser=argparse.ArgumentParser();parser.add_argument('--revision',required=True);parser.add_argument('--checkpoint',required=True)
    args=parser.parse_args();revision=args.revision
    full=subprocess.check_output(['git','rev-parse','--verify',revision+'^{commit}'],cwd=ROOT,text=True).strip()
    old=inspect(BACKEND);old_image=old['Config']['Image'];old_tag=old_image.rsplit(':',1)[-1]
    subprocess.run(['git','merge-base','--is-ancestor',old_tag,full],cwd=ROOT,check=True)
    checkpoint=json.loads(Path(args.checkpoint).read_text())
    if len(checkpoint['receipts'])!=2 or not all(row['verified'] and row['plaintext_bytes']>0 for row in checkpoint['receipts']):
        raise ValueError('verified_checkpoint_required')
    IMAGE='carwash-backend:'+revision
    subprocess.run(['docker','image','inspect',IMAGE],stdout=subprocess.DEVNULL,check=True)
    directory=ART/('cloud-backup-release-'+revision)
    directory.mkdir(mode=0o700,exist_ok=True)
    saved=directory/'backend-before.private.json'
    if saved.exists():
        previous=json.loads(saved.read_text())
        if previous['Config']['Image']!=old['Config']['Image']:raise ValueError('release_resume_image_conflict')
        old=previous
    private_write(saved,json.dumps(old))
    original=subprocess.check_output(['docker','exec',FRONTEND,'cat','/etc/nginx/conf.d/default.conf'],text=True)
    if 'backend:8000' not in original:raise ValueError('unexpected_frontend_route')
    private_write(directory/'frontend-before.conf',original)
    env=dict(item.split('=',1) for item in old['Config']['Env'])
    desired=old['Config']['Cmd']
    if env.get('LIVE_ASGI_ENABLED','false')=='true':desired=['gunicorn','-c','/app/asgi_gunicorn.conf.py','config.asgi:application']
    release=directory/'backend-release.private.yml'
    rollback=directory/'backend-rollback.private.yml'
    private_write(release,override(IMAGE,env,desired,old['Mounts']))
    private_write(rollback,override(old_image,env,desired,old['Mounts']))
    configured=subprocess.run(compose(release)+['config','--format','json'],cwd=SOURCE,capture_output=True,text=True,check=True)
    effective=json.loads(configured.stdout)['services']['backend']
    if effective['environment']!=env:raise ValueError('backend_environment_not_preserved')
    print('RELEASE_CONFIGURATION_PRESERVED',flush=True)
    db_env=dict(item.split('=',1) for item in inspect('carwash-db-1')['Config']['Env'])
    if env['DB_NAME']!=db_env['MYSQL_DATABASE']:raise ValueError('database_identity_mismatch')
    admin=dict(env);admin.update(DB_USER='root',DB_PASSWORD=db_env['MYSQL_ROOT_PASSWORD'],
        DB_ENGINE='mysql',CARWASH_INTERNAL_SCHEDULER='false',DJANGO_SETTINGS_MODULE='apps.vehicles.provisioning_settings')
    CODE="""import os,json
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
import django
django.setup()
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.core.management import call_command
executor=MigrationExecutor(connection)
plan=executor.migration_plan([('cloud_backup','0004_backuprun_retention_result')])
if any(migration.app_label!='cloud_backup' or backwards for migration,backwards in plan):raise ValueError('unexpected_migration_scope')
print('MIGRATION_PLAN '+json.dumps([migration.name for migration,_ in plan]),flush=True)
executor.migrate([('cloud_backup','0004_backuprun_retention_result')])
print('CLOUD_BACKUP_MIGRATIONS_APPLIED',flush=True)
"""
    result=run_env(['--rm','--network','carwash_default','--read-only','--cap-drop','ALL',
        '--security-opt','no-new-privileges','--tmpfs','/tmp:rw,mode=1777'],admin)
    if result.returncode:
        print('MIGRATION_FAILED_WITHOUT_SECRET_OUTPUT',flush=True);raise RuntimeError('migration_failed')
    print(result.stdout,flush=True)
    canary='carvash-backup-canary-'+revision
    canary_env=dict(env);canary_env['CARWASH_INTERNAL_SCHEDULER']='false'
    fd=os.memfd_create('carvash-canary-environment',0)
    try:
        os.write(fd,('\n'.join(k+'='+v for k,v in canary_env.items())+'\n').encode());os.lseek(fd,0,os.SEEK_SET)
        cmd=['docker','run','-d','--name',canary,'--network','carwash_default','--memory=1g','--memory-swap=1g','--cpus=1',
            '--env-file',f'/proc/self/fd/{fd}','--entrypoint',desired[0]]
        for item in old['Mounts']:
            spec='type=bind,src='+item['Source']+',dst='+item['Destination']
            if not item['RW']:spec+=',readonly'
            cmd+=['--mount',spec]
        subprocess.run([*cmd,IMAGE,*desired[1:]],pass_fds=(fd,),capture_output=True,text=True,check=True)
    finally:os.close(fd)
    if not health(canary):raise RuntimeError('canary_unhealthy')
    actual=dict(item.split('=',1) for item in inspect(canary)['Config']['Env'])
    if actual!=canary_env:raise ValueError('canary_environment_mismatch')
    print('CANARY_HEALTHY',flush=True)
    switched=False
    try:
        route(original.replace('backend:8000',canary+':8000'));switched=True
        print('FRONTEND_USING_HEALTHY_CANARY',flush=True)
        subprocess.run(compose(release)+['up','-d','--no-deps','--no-build','backend'],cwd=SOURCE,check=True)
        if not health(BACKEND):raise RuntimeError('released_backend_unhealthy')
        route(original);switched=False
        print('PRIMARY_BACKEND_HEALTHY_AND_ROUTING_RESTORED',flush=True)
    except Exception:
        print('ROLLING_BACK_BACKEND_IMAGE_WITHOUT_DATABASE_RESTORE',flush=True)
        subprocess.run(compose(rollback)+['up','-d','--no-deps','--no-build','backend'],cwd=SOURCE,check=True)
        if health(BACKEND):route(original);switched=False
        raise
    finally:
        if switched:print('HEALTHY_CANARY_ROUTE_RETAINED_FOR_SAFETY',flush=True)
    state={'revision':revision,'image':IMAGE,'previous_image':old_image,'release_file':str(release),
        'rollback_file':str(rollback),'canary':canary,'checkpoint':args.checkpoint,
        'media_host_path':next(item['Source'] for item in old['Mounts'] if item['Destination']=='/app/media')}
    private_write(directory/'release-state.json',json.dumps(state,indent=2))
    print('RELEASE_STATE '+str(directory/'release-state.json'),flush=True)

if __name__=='__main__':main()
