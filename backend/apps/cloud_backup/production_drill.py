"""Explicit approved restore drill against a network-isolated MySQL only.
Not discovered by ordinary test*.py runs; no production DB credentials loaded.
"""
import hashlib
import json
import os
from pathlib import Path
from unittest.mock import patch
from django.apps import apps
from django.core.exceptions import ImproperlyConfigured
from django.db import connections
from django.test import TransactionTestCase
from .archive import restore_fixture
from .chain_recovery import recover_chain,digest_file
from .delta import canonical
from .snapshot import GLOBAL,TENANT,CHILDREN,serialize_row,SnapshotError
from .staging import private_staging

if os.environ.get('CARVASH_APPROVED_RESTORE_DRILL')!='1':
    raise ImproperlyConfigured('Explicit restore drill approval required')
TARGETS=json.loads(os.environ['CARVASH_DRILL_TARGETS'])
if not TARGETS:raise ImproperlyConfigured('Explicit archive targets required')


def comparable_row(row):
    """Compare datetime instants exactly, independent of optional .000 formatting."""
    from datetime import timezone as datetime_timezone
    from django.db.models import DateTimeField
    model=apps.get_model(row['model'])
    row={**row,'fields':dict(row['fields'])}
    for field in model._meta.fields:
        value=row['fields'].get(field.name)
        if isinstance(field,DateTimeField) and value is not None:
            moment=field.to_python(value)
            if moment.tzinfo is not None:
                moment=moment.astimezone(datetime_timezone.utc)
            row['fields'][field.name]=moment.isoformat(timespec='microseconds')
    return row


class ProductionRestoreDrill(TransactionTestCase):
    databases={'default','recovery'}

    def restore_target(self,target):
        try:
            for alias in self.databases:
                config=connections[alias].settings_dict
                if (config['HOST']!='restore-db' or not config['NAME'].startswith('test_cloud_backup_')):
                    raise ValueError('isolated_database_required')
            tenant=int(target['tenant'])
            archives=[]
            for item in [target['full'],*target.get('increments',[])]:
                name=item['name']
                if Path(name).name!=name:raise ValueError('unsafe_archive_name')
                path=Path('/backups')/f'tenant-{tenant}'/name
                if path.is_symlink() or digest_file(path)!=item['sha256']:
                    raise ValueError('archive_identity_changed')
                archives.append(path)
            with private_staging(tenant) as stage:
                output=stage/'recovered'
                fixture=recover_chain(archives[0],archives[1:],tenant,output)
                expected={}
                counts={}
                field_hashes={}
                datetime_shapes={}
                for row in fixture:
                    row=comparable_row(row)
                    identity=(row['model'],str(row['pk']))
                    expected[identity]=hashlib.sha256(canonical(row)).hexdigest()
                    field_hashes[identity]={k:hashlib.sha256(canonical(v)).hexdigest() for k,v in row['fields'].items()}
                    from django.utils.dateparse import parse_datetime
                    datetime_shapes[identity]={k:v for k,v in row['fields'].items() if isinstance(v,str) and k.endswith('_at') and 'T' in v}
                    counts[row['model']]=counts.get(row['model'],0)+1
                row_count=len(fixture)
                del fixture
                # Only disposable migrated catalogs are cleared, never live DBs.
                for label in TENANT|set(CHILDREN)|{'cw_auth.carwash'}:
                    if apps.get_model(label).objects.using('recovery').exists():
                        raise ValueError('recovery_database_not_empty')
                for label in ['subscriptions.serviceplan','subscriptions.serviceproduct','subscriptions.platformproject']:
                    apps.get_model(label).objects.using('recovery').all().delete()
                with patch('apps.auth.support_tickets.notify_hq_alert_ticket_sms',side_effect=AssertionError('restore_sms_forbidden')):
                    restore_fixture(output/'fixture.json',tenant,'recovery')
                observed={}
                for label in TENANT|GLOBAL|set(CHILDREN)|{'cw_auth.carwash'}:
                    model=apps.get_model(label)
                    for obj in model.objects.using('recovery').all().iterator(chunk_size=100):
                        row=json.loads(serialize_row(obj))[0]
                        if label=='cw_auth.user':row['fields'].update(groups=[],user_permissions=[])
                        row=comparable_row(row)
                        identity=(row['model'],str(row['pk']))
                        digest=hashlib.sha256(canonical(row)).hexdigest()
                        if expected.get(identity)!=digest:
                            differences=[k for k in set(row['fields'])|set(field_hashes.get(identity,{})) if hashlib.sha256(canonical(row['fields'].get(k))).hexdigest()!=field_hashes.get(identity,{}).get(k)]
                            shapes={}
                            for k in differences:
                                a=datetime_shapes.get(identity,{}).get(k)
                                b=row['fields'].get(k)
                                if a and isinstance(b,str):
                                    left,right=parse_datetime(a),parse_datetime(b)
                                    shapes[k]={'expected_length':len(a),'observed_length':len(b),'delta_seconds':(right-left).total_seconds() if left and right else None}
                            print('RESTORE_TIME_SHAPES '+json.dumps(shapes),flush=True)
                            print('RESTORE_FIELD_DIAGNOSTIC '+json.dumps({'model':label,'fields':sorted(differences),'identity_present':identity in expected}),flush=True)
                            raise ValueError('restored_row_mismatch')
                        observed[identity]=digest
                if observed!=expected:raise ValueError('restored_identity_mismatch')
                roots=set(apps.get_model('cw_auth.carwash').objects.using('recovery').values_list('pk',flat=True))
                if roots!={tenant}:raise ValueError('tenant_isolation_failed')
                media=output/'media'
                file_count=sum(1 for item in media.rglob('*') if item.is_file()) if media.exists() else 0
                summary=hashlib.sha256(canonical([(list(key),value) for key,value in sorted(expected.items())])).hexdigest()
                print('RESTORE_RECEIPT '+json.dumps({'tenant':tenant,'run_id':target['run_id'],'rows':row_count,
                    'models':len(counts),'files':file_count,'increments':len(archives)-1,
                    'all_rows_equal':True,'tenant_isolated':True,'semantic_sha256':summary}),flush=True)
        except Exception as exc:
            # Never let SQL/deserializer exceptions expose customer records.
            safe={'isolated_database_required','unsafe_archive_name','archive_identity_changed','recovery_database_not_empty','restored_row_mismatch','restored_identity_mismatch','tenant_isolation_failed'}
            code=str(exc) if isinstance(exc,SnapshotError) or (isinstance(exc,ValueError) and str(exc) in safe) else type(exc).__name__
            raise AssertionError('isolated_restore_drill_failed:'+code) from None


def _case(target):
    def run(self):self.restore_target(target)
    return run

for index,target in enumerate(TARGETS):
    setattr(ProductionRestoreDrill,f'test_restore_{index}_tenant_{int(target["tenant"])}',_case(target))
