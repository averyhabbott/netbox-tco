from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_tco', '0004_pillar3_provisioning'),
    ]

    operations = [
        migrations.AddField(
            model_name='lineitem',
            name='name',
            field=models.CharField(blank=True, max_length=200),
        ),
    ]
