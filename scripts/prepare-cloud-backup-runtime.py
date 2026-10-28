#!/usr/bin/env python3
"""Materialize the approved worker configuration privately, without starting it."""
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
SOURCE=Path('/home/shivamouj/carvash-releases/source-master')
ART=Path('/mnt/extra-storage/carwash-rehearsal-artifacts')


def main():
    live=json.loads(subprocess.check_output(['docker','inspect','carwash-backend-1'],text=True))[0]
    image=live['Config']['Image'];revision=image.rsplit(':',1)[-1]
    media=next(item['Source'] for item in live['Mounts'] if item['Destination']=='/app/media')
    files=live['Config']['Labels']['com.docker.compose.project.config_files'].split(',')
    cmd=['docker','compose','-p','carwash','--profile','cloud-backup']
    for name in ['.env','.cloud-backup.private.env']:
        envpath=SOURCE/name
        if envpath.exists():cmd+=['--env-file',str(envpath)]
    for file in [*files,str(ROOT/'docker-compose.cloud-backup.yml'),str(ROOT/'docker-compose.cloud-backup-incremental.yml')]:cmd+=['-f',file]
    env=os.environ.copy();env.update(CLOUD_BACKUP_INCREMENTAL_IMAGE=image,CLOUD_BACKUP_LIVE_MEDIA_HOST_PATH=media)
    result=subprocess.run(cmd+['config','--format','json'],cwd=SOURCE,env=env,capture_output=True,text=True,check=True)
    model=json.loads(result.stdout);service=model['services']['cloud-backup']
    for key in ['build','depends_on','profiles']:service.pop(key,None)
    service['environment']={key:str(value).replace('$','$$') for key,value in service['environment'].items()}
    for item in service['volumes']:
        if item['type']!='bind':raise ValueError('unexpected_worker_volume')
        item.setdefault('bind',{})['create_host_path']=False
    mounted=next(item for item in service['volumes'] if item['target']=='/app/media')
    if mounted['source']!=media or not mounted['read_only']:raise ValueError('worker_media_mismatch')
    health="import os,io;os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings');import django;django.setup();from django.core.management import call_command;call_command('check_cloud_backup',stdout=io.StringIO());from apps.cloud_backup.models import BackupRun;BackupRun.objects.values_list('retention_status',flat=True).first()"
    service['healthcheck']={'test':['CMD','python','-c',health],'interval':'60s','timeout':'20s','retries':3,'start_period':'90s'}
    service['networks']={'default':None}
    service['ulimits']={'core':0}
    frozen={'services':{'cloud-backup':service},'networks':{'default':{'external':True,'name':'carwash_default'}},'secrets':model['secrets']}
    directory=ART/('cloud-backup-release-'+revision)
    path=directory/'worker-runtime.private.json'
    text=json.dumps(frozen,indent=2)
    if not path.exists() or path.read_text()!=text:
        active=subprocess.check_output(['docker','ps','-aq','--filter','name=^carwash-cloud-backup-1$'],text=True).strip()
        if active:raise ValueError('running_worker_configuration_differs')
        pending=path.with_suffix('.partial')
        fd=os.open(pending,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        try:
            with os.fdopen(fd,'w') as output:output.write(text);output.flush();os.fsync(output.fileno())
            os.replace(pending,path)
        finally:pending.unlink(missing_ok=True)
    subprocess.run(['docker','compose','-p','carwash','-f',str(path),'config','--quiet'],check=True)
    print('WORKER_CONFIGURATION '+str(path))
    print('WORKER_IMAGE '+image)
    print('WORKER_MEDIA_MATCHED_READ_ONLY')

if __name__=='__main__':main()
