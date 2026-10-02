from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_tco', '0002_qpi_ship_received_dates'),
    ]

    operations = [
        migrations.AddField(
            model_name='qpi',
            name='description',
            field=models.TextField(blank=True),
        ),
    ]
