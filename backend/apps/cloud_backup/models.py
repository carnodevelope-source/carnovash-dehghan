from django.db import models


class BackupRun(models.Model):
    # Deliberately not a cascading FK: deleting a tenant preserves backup history.
    tenant_id = models.PositiveBigIntegerField(db_index=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True)
    status = models.CharField(max_length=16, default='running')
    backup_kind = models.CharField(max_length=16, default='full')
    base_run_id = models.PositiveBigIntegerField(null=True, blank=True)
    parent_run_id = models.PositiveBigIntegerField(null=True, blank=True)
    error_code = models.CharField(max_length=48, blank=True)
    archive_name = models.CharField(max_length=100, blank=True)
    size_bytes = models.PositiveBigIntegerField(default=0)
    retained_bytes = models.PositiveBigIntegerField(default=0)
    sha256 = models.CharField(max_length=64, blank=True)
    verified_at = models.DateTimeField(null=True)
    # Verification authenticates all chunks and checks each member's digest.
    recovery_status = models.CharField(max_length=32, default='unverified')
