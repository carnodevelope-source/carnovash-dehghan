"""Explicitly enabled, logged, verified retention after a successful backup."""
import json
from django.utils import timezone
from .models import BackupRun
from .retention_service import retain_tenant
from .snapshot import SnapshotError


def maintain_run(run, *, output=lambda text: None):
    if run.status != 'success' or run.recovery_status != 'integrity_verified':
        raise SnapshotError('unverified_archive')
    try:
        plan = retain_tenant(run.tenant_id)
        # Log the exact plan before any deletion. The token is rechecked under
        # the same tenant lock by retain_tenant before applying the plan.
        output(json.dumps({'tenant':run.tenant_id,'retention_plan':plan},sort_keys=True))
        retain_tenant(run.tenant_id,execute=True,reviewed_token=plan['token'])
        BackupRun.objects.filter(pk=run.pk).update(retention_status='success',
            retention_error_code='',retention_checked_at=timezone.now())
        return True
    except Exception as exc:
        safe={'subscription_inactive','unmanaged_archive','invalid_chain_history',
              'checksum_mismatch','missing_archive','retention_plan_changed',
              'archive_still_required','mount_unavailable','no_verified_replacement'}
        code=str(exc) if isinstance(exc,SnapshotError) and str(exc) in safe else 'retention_failed'
        BackupRun.objects.filter(pk=run.pk).update(retention_status='failed',
            retention_error_code=code,retention_checked_at=timezone.now())
        output(f'tenant={run.tenant_id} retention=failed code={code}')
        return False
