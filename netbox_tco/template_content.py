from datetime import date
from decimal import Decimal

from django.urls import reverse
from netbox.plugins import PluginTemplateExtension


class DeviceTCOPanel(PluginTemplateExtension):
    """Adds hardware, annual recurring, lifetime, and per-port cost to the Device detail page."""
    models = ['dcim.device']

    def right_page(self):
        device = self.context['object']

        from dcim.models import Module
        from django.contrib.contenttypes.models import ContentType
        from django.db.models import Q
        from netbox.plugins import get_plugin_config
        from .choices import BillingTermChoices, ContractStatusChoices
        from .models import CoverageLine, LicenseLine, ProvisionedItem

        include_modules = get_plugin_config('netbox_tco', 'hardware_price_sum')
        device_ct = ContentType.objects.get_for_model(device.__class__)
        module_ct = ContentType.objects.get_for_model(Module)
        module_ids = list(device.modules.values_list('pk', flat=True)) if include_modules else []

        # Source line item for this device
        try:
            pi = ProvisionedItem.objects.select_related('line_item__qpi').get(
                content_type=device_ct, object_id=device.pk
            )
            source_line_item = pi.line_item
            source_qpi = pi.line_item.qpi
        except ProvisionedItem.DoesNotExist:
            source_line_item = None
            source_qpi = None

        # Hardware cost (device + installed modules when hardware_price_sum is enabled)
        hardware_cost = None
        if source_line_item:
            hardware_cost = source_line_item.unit_price
            for mpi in ProvisionedItem.objects.filter(
                content_type=module_ct, object_id__in=module_ids,
            ).select_related('line_item'):
                hardware_cost += mpi.line_item.unit_price

        # Coverage and license lines on the device and (optionally) its installed modules;
        # cancelled contracts/licenses excluded
        assigned = Q(assigned_object_type=device_ct, assigned_object_id=device.pk)
        if module_ids:
            assigned |= Q(assigned_object_type=module_ct, assigned_object_id__in=module_ids)
        all_coverage = CoverageLine.objects.filter(assigned).exclude(
            support_contract__status=ContractStatusChoices.STATUS_CANCELLED,
        )
        all_licenses = LicenseLine.objects.filter(assigned).exclude(
            license__status=ContractStatusChoices.STATUS_CANCELLED,
        )

        # Perpetual licenses count toward lifetime cost only, never annual recurring
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
        recurring_to_date = sum((l.price for l in all_coverage), Decimal('0')) + \
            sum((l.price for l in all_licenses), Decimal('0'))
        if hardware_cost is not None or all_coverage.exists() or all_licenses.exists():
            lifetime_cost = (hardware_cost or Decimal('0')) + recurring_to_date

        # Per-port cost
        per_port = None
        if hardware_cost is not None or annual_recurring is not None:
            port_types = get_plugin_config('netbox_tco', 'port_interface_types')
            port_count = device.interfaces.filter(type__in=port_types).count()
            total_cost = (hardware_cost or Decimal('0')) + (annual_recurring or Decimal('0'))
            if port_count > 0:
                per_port = total_cost / port_count

        return self.render('netbox_tco/inc/device_tco.html', extra_context={
            'source_line_item': source_line_item,
            'source_qpi': source_qpi,
            'hardware_cost': hardware_cost,
            'annual_recurring': annual_recurring,
            'lifetime_cost': lifetime_cost,
            'per_port': per_port,
            'includes_modules': bool(module_ids),
        })


class AttachListButton(PluginTemplateExtension):
    """'Attach TCO Item' button on the core Device and Module list pages."""
    models = ['dcim.device', 'dcim.module']

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


class TypeEOLPanel(PluginTemplateExtension):
    """Which lifecycle record a device/module type belongs to (or a link to start one)."""
    models = ['dcim.devicetype', 'dcim.moduletype']

    def right_page(self):
        from .models import LifecycleRecord
        type_obj = self.context['object']
        record = LifecycleRecord.for_type(type_obj)
        field = 'device_types' if type_obj._meta.model_name == 'devicetype' else 'module_types'
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


template_extensions = [DeviceTCOPanel, DeviceEOLPanel, ModuleEOLPanel, TypeEOLPanel, AttachListButton]
