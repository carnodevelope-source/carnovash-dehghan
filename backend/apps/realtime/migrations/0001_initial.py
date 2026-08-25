from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name='LiveOutbox',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tenant_id', models.BigIntegerField(blank=True, null=True)),
                ('actor_user_id', models.BigIntegerField(blank=True, null=True)),
                ('event_type', models.CharField(max_length=80)),
                ('entity_type', models.CharField(blank=True, max_length=40)),
                ('entity_id', models.CharField(blank=True, max_length=100)),
                ('payload', models.JSONField(default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'indexes': [
                    models.Index(fields=['tenant_id', 'id'], name='live_outbox_tenant_id_idx'),
                    models.Index(fields=['created_at'], name='live_outbox_created_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='IdempotencyRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tenant_id', models.BigIntegerField(default=0)),
                ('key', models.CharField(max_length=128)),
                ('method', models.CharField(max_length=10)),
                ('path', models.CharField(max_length=255)),
                ('request_hash', models.CharField(max_length=64)),
                ('status_code', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('response_json', models.JSONField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='idempotency_records', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'indexes': [models.Index(fields=['created_at'], name='idempotency_created_idx')],
            },
        ),
        migrations.AddConstraint(
            model_name='idempotencyrecord',
            constraint=models.UniqueConstraint(fields=('tenant_id', 'user', 'key'), name='uniq_idempotency_tenant_user_key'),
        ),
    ]
