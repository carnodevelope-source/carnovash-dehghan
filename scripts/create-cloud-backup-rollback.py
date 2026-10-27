#!/usr/bin/env python3
"""Create encrypted, authenticated SQL/media checkpoints before deployment.
Secrets stay in memory and mounted secret files. Never writes plaintext dumps.
"""
import datetime
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
SOURCE=Path('/home/shivamouj/carvash-releases/source-master')
ART=Path('/mnt/extra-storage/carwash-rehearsal-artifacts')


def configuration():
    live=json.loads(subprocess.check_output(['docker','inspect','carwash-backend-1'],text=True))[0]
    files=live['Config']['Labels']['com.docker.compose.project.config_files'].split(',')
    media=next(m['Source'] for m in live['Mounts'] if m['Destination']=='/app/media')
    cmd=['docker','compose','-p','carwash','--profile','cloud-backup']
    for name in ['.env','.cloud-backup.private.env']:
        path=SOURCE/name
        if path.is_file():cmd+=['--env-file',str(path)]
    for file in [*files,str(ROOT/'docker-compose.cloud-backup.yml'),str(ROOT/'docker-compose.cloud-backup-incremental.yml')]:cmd+=['-f',file]
    env=os.environ.copy()
    live_env=dict(item.split('=',1) for item in live['Config']['Env'])
    env['RUNTIME_DB_PASSWORD']=live_env['DB_PASSWORD']
    env.update(CLOUD_BACKUP_INCREMENTAL_IMAGE='carvash-cloud-backup-review:7c5cf44',CLOUD_BACKUP_LIVE_MEDIA_HOST_PATH=media)
    result=subprocess.run(cmd+['config','--format','json'],cwd=SOURCE,env=env,capture_output=True,text=True,check=True)
    config=json.loads(result.stdout)
    return config,media


CONSUMER = r"""import os,sys,json,hashlib,zlib,io,gzip
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
import django
django.setup()
from apps.cloud_backup import service
from apps.cloud_backup.archive import EncryptWriter,DecryptReader
from pathlib import Path
folder,name=sys.argv[1:3]
with service.pinned_root() as root:
    directory=root/'deployment-rollback'/folder
    (root/'deployment-rollback').mkdir(mode=0o700,exist_ok=True)
    directory.mkdir(mode=0o700,exist_ok=True)
    with service.pinned_tenant(directory) as directory:
        path=directory/(name+'.partial')
        final=directory/name
        digest=hashlib.sha256();size=0;tail=b''
        fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        try:
            with os.fdopen(fd,'wb') as output:
                writer=EncryptWriter(output,service.write_guard)
                compressor=zlib.compressobj(6,zlib.DEFLATED,31)
                while chunk:=sys.stdin.buffer.read(1024*1024):
                    digest.update(chunk);size+=len(chunk);tail=(tail+chunk)[-4096:]
                    writer.write(compressor.compress(chunk))
                if size==0:raise ValueError('empty_checkpoint')
                if name.startswith('database') and b'-- Dump completed on' not in tail:raise ValueError('incomplete_sql_dump')
                writer.write(compressor.flush());writer.finish()
                output.flush();os.fsync(output.fileno())
            checked=hashlib.sha256()
            with path.open('rb') as source,io.BufferedReader(DecryptReader(source)) as encrypted,gzip.GzipFile(fileobj=encrypted) as plain:
                while chunk:=plain.read(1024*1024):checked.update(chunk)
                while encrypted.read(1024*1024):raise ValueError('trailing_data')
            if digest.digest()!=checked.digest():raise ValueError('checkpoint_mismatch')
            service.write_guard();os.replace(path,final);service.sync_directory(directory)
            print(json.dumps({'name':name,'plaintext_bytes':size,'plaintext_sha256':digest.hexdigest(),
                'encrypted_bytes':final.stat().st_size,'encrypted_sha256':service.archive_digest(final),'verified':True}))
        finally:
            path.unlink(missing_ok=True)
"""


def main():
    config,media=configuration()
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    env=config['services']['cloud-backup']['environment']
    env['DB_ENGINE']='sqlite'
    envtext='\n'.join(k+'='+str(v) for k,v in env.items())+'\n'
    # Replace literal escapes after source generation; no shell sees values.
    envtext=envtext.replace('\\n','\n')
    key=config['secrets']['cloud_backup_key']['file']
    common=['docker','run','-i','--rm','--network','none','--read-only','--user','10001:10001','--cap-drop','ALL',
        '--security-opt','no-new-privileges','--cpus=0.5','--memory=512m','--memory-swap=512m',
        '--tmpfs','/tmp:rw,mode=1777','--env-file','/dev/stdin']
    # Anonymous FD keeps credentials out of argv and named temporary files.
    envfd=os.memfd_create('carvash-checkpoint-env',0)
    os.write(envfd,envtext.encode())
    common[-1]=f'/proc/self/fd/{envfd}'
    common+=['--mount','type=bind,src=/mnt/extra-storage,dst=/mnt/extra-storage,readonly',
        '--mount','type=bind,src=/mnt/extra-storage/cloud-backups,dst=/mnt/extra-storage/cloud-backups',
        '--mount','type=bind,src=/proc/1/mountinfo,dst=/run/host-mountinfo,readonly',
        '--mount','type=bind,src='+key+',dst=/run/secrets/cloud_backup_key,readonly',
        '--entrypoint','python','carvash-cloud-backup-review:7c5cf44','-u','-c',CONSUMER,stamp]
    inputs=[('database.sql.gz.aesgcm',['docker','exec','carwash-db-1','sh','-c',
        'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysqldump --user=root --single-transaction --routines --triggers --events --no-tablespaces --set-gtid-purged=OFF --hex-blob "$MYSQL_DATABASE"']),
        ('media.tar.gz.aesgcm',['docker','run','--rm','--network','none','--read-only','--user','0:0','--cap-drop','ALL',
         '--security-opt','no-new-privileges','--mount','type=bind,src='+media+',dst=/media,readonly',
         '--entrypoint','tar','carvash-cloud-backup-review:7c5cf44','-C','/media','-cf','-','.'])]
    receipts=[]
    try:
        for name,command in inputs:
            producer=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            os.lseek(envfd,0,os.SEEK_SET)
            consumer=subprocess.run([*common,name],stdin=producer.stdout,pass_fds=(envfd,),capture_output=True,text=True)
            producer.stdout.close()
            code=producer.wait(timeout=600)
            if code or consumer.returncode:
                print(json.dumps({'checkpoint_failed':name,'producer_exit':code,'consumer_exit':consumer.returncode}))
                raise SystemExit(1)
            receipt=json.loads(consumer.stdout);receipts.append(receipt);print(json.dumps(receipt),flush=True)
        manifest={'checkpoint':stamp,'directory':'/mnt/extra-storage/cloud-backups/deployment-rollback/'+stamp,'receipts':receipts}
        path=ART/('cloud-backup-checkpoint-'+stamp+'.json')
        fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w') as output:json.dump(manifest,output,indent=2);output.flush();os.fsync(output.fileno())
        print('CHECKPOINT_MANIFEST '+str(path),flush=True)
    finally:
        os.close(envfd)

if __name__=='__main__':main()
