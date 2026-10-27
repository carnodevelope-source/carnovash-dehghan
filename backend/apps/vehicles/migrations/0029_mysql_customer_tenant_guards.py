from django.db import migrations
from apps.vehicles.mysql_guards import install, uninstall


def forwards(apps, schema_editor):
    install(schema_editor.connection)


def backwards(apps, schema_editor):
    uninstall(schema_editor.connection)


class Migration(migrations.Migration):
    atomic = False
    dependencies = [('vehicles', '0028_customertenantauthorization')]
    operations = [migrations.RunPython(forwards, backwards)]
