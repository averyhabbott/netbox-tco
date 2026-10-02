"""
Central registry of provisionable model types.

Each entry maps a LineItem hardware sub-type to its metadata. This is the single
place to update when a new provisionable type is added (e.g. InventoryItem in a
future pillar). Adding a new type also requires:
  1. A new FK on LineItem (migration)
  2. An entry here
  3. A migration to add the CF object_type to the new model
"""

from django.db.models import Q

PROVISIONABLE_TYPES = [
    {
        'line_item_fk': 'device_type',   # FK field on LineItem identifying the sub-type
        'model': 'dcim.Device',
        'model_name': 'device',          # lowercase — used in ContentType / Q lookups
        'add_url': '/dcim/devices/add/',
        'coverable': True,               # can carry support coverage / license lines
    },
    {
        'line_item_fk': 'module_type',
        'model': 'dcim.Module',
        'model_name': 'module',
        'add_url': '/dcim/modules/add/',
        'coverable': True,
    },
    {
        'line_item_fk': 'rack_type',
        'model': 'dcim.Rack',
        'model_name': 'rack',
        'add_url': '/dcim/racks/add/',
        'coverable': False,
    },
]


def provisionable_model_names():
    """List of lowercase model names, e.g. ['device', 'module', 'rack']."""
    return [t['model_name'] for t in PROVISIONABLE_TYPES]


def provisionable_limit_choices_to():
    """Q object suitable for limit_choices_to on ProvisionedItem.content_type."""
    return Q(app_label='dcim', model__in=provisionable_model_names())


def get_provisionable_models():
    """Return Django model classes for all provisionable types (deferred import)."""
    from django.apps import apps
    return [apps.get_model(t['model']) for t in PROVISIONABLE_TYPES]


def entry_for_line_item(line_item):
    """Return the registry entry whose line_item_fk is set on this line item, or None."""
    for entry in PROVISIONABLE_TYPES:
        if getattr(line_item, entry['line_item_fk']) is not None:
            return entry
    return None


def coverable_model_names():
    """Lowercase model names that can be assigned to coverage lines, e.g. ['device', 'module']."""
    return [t['model_name'] for t in PROVISIONABLE_TYPES if t['coverable']]


def coverable_limit_choices_to():
    return Q(app_label='dcim', model__in=coverable_model_names())


def get_coverable_models():
    from django.apps import apps
    return [apps.get_model(t['model']) for t in PROVISIONABLE_TYPES if t['coverable']]
