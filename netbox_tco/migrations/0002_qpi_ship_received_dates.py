from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_tco', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='qpi',
            name='shipping_receiving',
        ),
        migrations.AddField(
            model_name='qpi',
            name='ship_date',
            field=models.DateField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='qpi',
            name='received_date',
            field=models.DateField(null=True, blank=True),
        ),
    ]
