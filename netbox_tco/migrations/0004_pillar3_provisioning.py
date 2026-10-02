import django.db.models
from django.db import migrations, models
import django.db.models.deletion


def create_tco_line_item_custom_field(apps, schema_editor):
    from extras.choices import CustomFieldTypeChoices
    from extras.models import CustomField
    from django.contrib.contenttypes.models import ContentType

    try:
        lineitem_ct = ContentType.objects.get(app_label='netbox_tco', model='lineitem')
    except ContentType.DoesNotExist:
        return

    cf, _ = CustomField.objects.get_or_create(
        name='tco_line_item',
        defaults={
            'type': CustomFieldTypeChoices.TYPE_OBJECT,
            'related_object_type': lineitem_ct,
            'label': 'TCO Line Item',
            'description': 'Source QPI line item that funded this provisioned object',
            'required': False,
        },
    )

    for model_name in ('device', 'module', 'rack'):
        try:
            ct = ContentType.objects.get(app_label='dcim', model=model_name)
            cf.object_types.add(ct)
        except ContentType.DoesNotExist:
            pass


def remove_tco_line_item_custom_field(apps, schema_editor):
    from extras.models import CustomField
    CustomField.objects.filter(name='tco_line_item').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_tco', '0003_qpi_description'),
        ('contenttypes', '0002_remove_content_type_name'),
        ('dcim', '0001_initial'),
    ]

    operations = [
        # Remove old provisioned_devices M2M
        migrations.RemoveField(
            model_name='lineitem',
            name='provisioned_devices',
        ),

        # Add module_type FK
        migrations.AddField(
            model_name='lineitem',
            name='module_type',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='netbox_tco_line_items',
                to='dcim.moduletype',
            ),
        ),

        # Add rack_type FK
        migrations.AddField(
            model_name='lineitem',
            name='rack_type',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='netbox_tco_line_items',
                to='dcim.racktype',
            ),
        ),

        # Create ProvisionedItem junction model
        migrations.CreateModel(
            name='ProvisionedItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('object_id', models.PositiveBigIntegerField()),
                ('content_type', models.ForeignKey(
                    limit_choices_to=django.db.models.Q(
                        app_label='dcim', model__in=['device', 'module', 'rack']
                    ),
                    on_delete=django.db.models.deletion.CASCADE,
                    to='contenttypes.contenttype',
                )),
                ('line_item', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='provisioned_items',
                    to='netbox_tco.lineitem',
                )),
            ],
            options={
                'ordering': ['content_type', 'object_id'],
                'unique_together': {('content_type', 'object_id')},
            },
        ),

        # Create tco_line_item custom field on Device, Module, Rack
        migrations.RunPython(
            create_tco_line_item_custom_field,
            reverse_code=remove_tco_line_item_custom_field,
        ),
    ]
