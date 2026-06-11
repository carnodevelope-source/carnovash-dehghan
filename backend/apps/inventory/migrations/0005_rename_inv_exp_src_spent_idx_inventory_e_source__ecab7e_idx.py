from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0004_expenseentry'),
    ]

    operations = [
        migrations.RenameIndex(
            model_name='expenseentry',
            new_name='inventory_e_source__ecab7e_idx',
            old_name='inv_exp_src_spent_idx',
        ),
    ]
