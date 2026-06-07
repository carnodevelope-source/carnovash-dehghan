from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0002_product_tenant_productcategory_tenant'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='description',
            field=models.TextField(blank=True),
        ),
    ]
