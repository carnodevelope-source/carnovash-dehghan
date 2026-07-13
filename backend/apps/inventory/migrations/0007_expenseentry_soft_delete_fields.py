from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0006_expenseentry_attachment_and_spent_at'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='expenseentry',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='expenseentry',
            name='deleted_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='expense_entries_deleted', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='expenseentry',
            name='is_deleted',
            field=models.BooleanField(default=False),
        ),
    ]
