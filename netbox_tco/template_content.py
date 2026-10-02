from datetime import date
from decimal import Decimal

from django.urls import reverse
from netbox.plugins import PluginTemplateExtension


def cost_summary(targets):
    """
    Hardware, annual recurring, and lifetime cost for a set of objects, given as
    (model class, [pks]) pairs. Each figure is None when nothing contributes to it.
    Cancelled contracts/licenses are excluded; perpetual licenses count toward lifetime only.
    """
    from django.contrib.contenttypes.models import ContentType
    from django.db.models import Q
    from .choices import BillingTermChoices, ContractStatusChoices
    from .models import CoverageLine, LicenseLine, ProvisionedItem

    provisioned = Q(pk__in=[])
    assigned = Q(pk__in=[])
    for model, pks in targets:
        if not pks:
            continue
        ct = ContentType.objects.get_for_model(model)
        provisioned |= Q(content_type=ct, object_id__in=pks)
        assigned |= Q(assigned_object_type=ct, assigned_object_id__in=pks)

    hardware = ProvisionedItem.objects.filter(provisioned).select_related('line_item')
    hardware_cost = None
    for pi in hardware:
        hardware_cost = (hardware_cost or Decimal('0')) + pi.line_item.unit_price

    all_coverage = CoverageLine.objects.filter(assigned).exclude(
        support_contract__status=ContractStatusChoices.STATUS_CANCELLED,
    )
    all_licenses = LicenseLine.objects.filter(assigned).exclude(
        license__status=ContractStatusChoices.STATUS_CANCELLED,
    )

    today = date.today()
    current_coverage = all_coverage.filter(start_date__lte=today, end_date__gte=today)
    current_licenses = all_licenses.filter(
        billing_term=BillingTermChoices.TERM_SUBSCRIPTION, start_date__lte=today, end_date__gte=today,
    )

    def annualize(lines):
        total = Decimal('0')
        for line in lines:
            if line.start_date and line.end_date and line.price:
                days = (line.end_date - line.start_date).days or 1
                total += line.price * Decimal('365') / Decimal(days)
        return total

    annual_recurring = None
    if current_coverage.exists() or current_licenses.exists():
        annual_recurring = annualize(current_coverage) + annualize(current_licenses)

    lifetime_cost = None
    if hardware_cost is not None or all_coverage.exists() or all_licenses.exists():
        recurring_to_date = sum((l.price for l in all_coverage), Decimal('0')) + \
            sum((l.price for l in all_licenses), Decimal('0'))
        lifetime_cost = (hardware_cost or Decimal('0')) + recurring_to_date

    return {
        'hardware_cost': hardware_cost,
        'annual_recurring': annual_recurring,
        'lifetime_cost': lifetime_cost,
    }


def _source(obj):
    """(line item, QPI) that purchased this object, or (None, None)."""
    from django.contrib.contenttypes.models import ContentType
    from .models import ProvisionedItem
    pi = ProvisionedItem.objects.select_related('line_item__qpi').filter(
        content_type=ContentType.objects.get_for_model(obj.__class__), object_id=obj.pk,
    ).first()
    return (pi.line_item, pi.line_item.qpi) if pi else (None, None)


class DeviceTCOPanel(PluginTemplateExtension):
    """Adds hardware, annual recurring, lifetime, and per-port cost to the Device detail page."""
    models = ['dcim.device']

    def right_page(self):
        from dcim.models import Module
        from netbox.plugins import get_plugin_config

        device = self.context['object']
        include_modules = get_plugin_config('netbox_tco', 'hardware_price_sum')
        module_ids = list(device.modules.values_list('pk', flat=True)) if include_modules else []

        source_line_item, source_qpi = _source(device)
        costs = cost_summary([(device.__class__, [device.pk]), (Module, module_ids)])

        # Per-port cost
        per_port = None
        if costs['hardware_cost'] is not None or costs['annual_recurring'] is not None:
            port_types = get_plugin_config('netbox_tco', 'port_interface_types')
            port_count = device.interfaces.filter(type__in=port_types).count()
            total_cost = (costs['hardware_cost'] or Decimal('0')) + (costs['annual_recurring'] or Decimal('0'))
            if port_count > 0:
                per_port = total_cost / port_count

        return self.render('netbox_tco/inc/device_tco.html', extra_context={
            'source_line_item': source_line_item,
            'source_qpi': source_qpi,
            **costs,
            'per_port': per_port,
            'includes_modules': bool(module_ids),
        })


class RackTCOPanel(PluginTemplateExtension):
    """
    The rack's own cost (its purchase plus support/licenses on the rack itself), and separately
    the rack plus everything mounted in it. Rack cost is never split across its devices.
    """
    models = ['dcim.rack']

    def right_page(self):
        from dcim.models import Device, Module
        from netbox.plugins import get_plugin_config

        rack = self.context['object']
        include_modules = get_plugin_config('netbox_tco', 'hardware_price_sum')
        device_ids = list(Device.objects.filter(rack=rack).values_list('pk', flat=True))
        module_ids = list(
            Module.objects.filter(device__rack=rack).values_list('pk', flat=True)
        ) if include_modules else []

        source_line_item, source_qpi = _source(rack)
        own = cost_summary([(rack.__class__, [rack.pk])])
        loaded = cost_summary([(rack.__class__, [rack.pk]), (Device, device_ids), (Module, module_ids)])
        if source_line_item is None and all(v is None for v in (*own.values(), *loaded.values())):
            return ''
        rows = [
            ('Hardware (one-time)', own['hardware_cost'], loaded['hardware_cost'], False),
            ('Annual recurring', own['annual_recurring'], loaded['annual_recurring'], False),
            ('Lifetime cost', own['lifetime_cost'], loaded['lifetime_cost'], True),
        ]
        return self.render('netbox_tco/inc/rack_tco.html', extra_context={
            'source_line_item': source_line_item,
            'source_qpi': source_qpi,
            'rows': [r for r in rows if r[1] is not None or r[2] is not None],
            'device_count': len(device_ids),
            'includes_modules': bool(module_ids),
        })


class AttachListButton(PluginTemplateExtension):
    """'Attach TCO Item' button on the core Device, Module, and Rack list pages."""
    models = ['dcim.device', 'dcim.module', 'dcim.rack']

    def list_buttons(self):
        user = self.context['request'].user
        model_name = self.context['object']._meta.model_name
        if not any(user.has_perm(p) for p in (
            f'dcim.change_{model_name}', 'netbox_tco.change_coverageline', 'netbox_tco.change_licenseline',
        )):
            return ''
        return self.render('netbox_tco/inc/attach_list_button.html', extra_context={
            'attach_url': reverse('plugins:netbox_tco:attach_tco_item', kwargs={'model_name': model_name}),
        })


def milestone_rows(record, today=None):
    """
    A record's milestones with a highlight state: 'past' once the date has passed, 'soon' within the
    global 'approaching' renewal threshold (the same lead time Pillar 7 uses for renewals).
    """
    today = today or date.today()
    soon_days = _soon_days()
    rows = []
    for m in sorted(record.milestones.all(), key=lambda m: m.date):
        days = (m.date - today).days
        rows.append({
            'milestone': m,
            'state': 'past' if days < 0 else 'soon' if days <= soon_days else '',
            'days': days,
        })
    return rows


def _soon_days():
    from netbox.plugins import get_plugin_config
    return get_plugin_config('netbox_tco', 'renewal_thresholds').get('approaching', 90)


class DeviceEOLPanel(PluginTemplateExtension):
    """EOS/EOL dates for the device's type, plus its installed modules' types."""
    models = ['dcim.device']

    def left_page(self):
        from .models import LifecycleRecord
        device = self.context['object']
        record = LifecycleRecord.for_type(device.device_type)

        # Installed modules, grouped by the record covering their module type
        groups = {}
        for module in device.modules.select_related('module_type', 'module_bay').order_by('module_bay__name'):
            module_record = LifecycleRecord.for_type(module.module_type)
            if module_record:
                groups.setdefault(module_record.pk, {'record': module_record, 'modules': []})['modules'].append(module)
        module_groups = [
            {**g, 'rows': milestone_rows(g['record'])}
            for g in sorted(groups.values(), key=lambda g: g['record'].name)
        ]

        if not record and not module_groups:
            return ''
        return self.render('netbox_tco/inc/lifecycle_panel.html', extra_context={
            'record': record,
            'rows': milestone_rows(record) if record else [],
            'module_groups': module_groups,
            'soon_days': _soon_days(),
        })


class ModuleEOLPanel(PluginTemplateExtension):
    """EOS/EOL dates for the module's type."""
    models = ['dcim.module']

    def left_page(self):
        from .models import LifecycleRecord
        record = LifecycleRecord.for_type(self.context['object'].module_type)
        if not record:
            return ''
        return self.render('netbox_tco/inc/lifecycle_panel.html', extra_context={
            'record': record,
            'rows': milestone_rows(record),
            'soon_days': _soon_days(),
        })


class RackEOLPanel(PluginTemplateExtension):
    """EOS/EOL dates for the rack's type."""
    models = ['dcim.rack']

    def left_page(self):
        from .models import LifecycleRecord
        record = LifecycleRecord.for_type(self.context['object'].rack_type)
        if not record:
            return ''
        return self.render('netbox_tco/inc/lifecycle_panel.html', extra_context={
            'record': record,
            'rows': milestone_rows(record),
            'soon_days': _soon_days(),
        })


TYPE_FIELDS = {'devicetype': 'device_types', 'moduletype': 'module_types', 'racktype': 'rack_types'}


class TypeEOLPanel(PluginTemplateExtension):
    """Which lifecycle record a device/module/rack type belongs to (or a link to start one)."""
    models = ['dcim.devicetype', 'dcim.moduletype', 'dcim.racktype']

    def right_page(self):
        from .models import LifecycleRecord
        type_obj = self.context['object']
        record = LifecycleRecord.for_type(type_obj)
        field = TYPE_FIELDS[type_obj._meta.model_name]
        add_url = None
        if not record and self.context['request'].user.has_perm('netbox_tco.add_lifecyclerecord'):
            add_url = (
                f"{reverse('plugins:netbox_tco:lifecyclerecord_add')}?{field}={type_obj.pk}"
                f"&return_url={type_obj.get_absolute_url()}"
            )
        return self.render('netbox_tco/inc/lifecycle_panel.html', extra_context={
            'record': record,
            'rows': milestone_rows(record) if record else [],
            'soon_days': _soon_days(),
            'show_empty': True,
            'add_url': add_url,
        })


template_extensions = [
    DeviceTCOPanel, RackTCOPanel, DeviceEOLPanel, ModuleEOLPanel, RackEOLPanel, TypeEOLPanel, AttachListButton,
]
