from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver


def _sync_tco_line_item(sender, instance, **kwargs):
    """
    When a Device, Module, or Rack is saved with a tco_line_item custom field value,
    create or update the corresponding ProvisionedItem record. Clears the record when
    the custom field is removed.
    """
    try:
        from .models import LineItem, ProvisionedItem
        line_item_pk = instance.custom_field_data.get('tco_line_item')
        ct = ContentType.objects.get_for_model(sender)

        if line_item_pk:
            try:
                line_item = LineItem.objects.get(pk=line_item_pk)
                ProvisionedItem.objects.update_or_create(
                    content_type=ct,
                    object_id=instance.pk,
                    defaults={'line_item': line_item},
                )
            except LineItem.DoesNotExist:
                ProvisionedItem.objects.filter(content_type=ct, object_id=instance.pk).delete()
        else:
            ProvisionedItem.objects.filter(content_type=ct, object_id=instance.pk).delete()
    except Exception:
        pass


def _cleanup_provisioned_item(sender, instance, **kwargs):
    """Remove ProvisionedItem when its target object is deleted via any path."""
    try:
        from .models import ProvisionedItem
        ct = ContentType.objects.get_for_model(sender)
        ProvisionedItem.objects.filter(content_type=ct, object_id=instance.pk).delete()
    except Exception:
        pass


def _retire_lines(sender, instance, **kwargs):
    """Unlink coverage/license lines from a deleted device/module and mark them Retired (price still counts)."""
    from .choices import CoverageStatusChoices
    from .models import CoverageLine, LicenseLine
    ct = ContentType.objects.get_for_model(sender)
    for line_model in (CoverageLine, LicenseLine):
        for line in line_model.objects.filter(assigned_object_type=ct, assigned_object_id=instance.pk):
            line.snapshot()
            line.assigned_object_type = None
            line.assigned_object_id = None
            line.status = CoverageStatusChoices.STATUS_RETIRED
            line.save()


def _delete_attachments(sender, instance, **kwargs):
    """Attachments hang off a generic FK, so delete them (and their files) with their parent."""
    from .models import Attachment
    ct = ContentType.objects.get_for_model(sender)
    for att in Attachment.objects.filter(content_type=ct, object_id=instance.pk):
        att.delete()


def register_signals():
    from .provisioning import get_coverable_models, get_provisionable_models
    for model in get_provisionable_models():
        post_save.connect(_sync_tco_line_item, sender=model, weak=False)
        pre_delete.connect(_cleanup_provisioned_item, sender=model, weak=False)
    for model in get_coverable_models():
        pre_delete.connect(_retire_lines, sender=model, weak=False)
    from .models import License, LifecycleRecord, QPI, SupportContract
    for model in (QPI, SupportContract, License, LifecycleRecord):
        pre_delete.connect(_delete_attachments, sender=model, weak=False)
