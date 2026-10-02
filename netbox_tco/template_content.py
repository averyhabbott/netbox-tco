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
        from .choices import ContractStatusChoices
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

        # Coverage on the device and (optionally) its installed modules; cancelled contracts excluded
        covered = Q(assigned_object_type=device_ct, assigned_object_id=device.pk)
        if module_ids:
            covered |= Q(assigned_object_type=module_ct, assigned_object_id__in=module_ids)
        all_coverage = CoverageLine.objects.filter(covered).exclude(
            support_contract__status=ContractStatusChoices.STATUS_CANCELLED,
        )
        all_licenses = LicenseLine.objects.filter(device=device).exclude(
            license__status=ContractStatusChoices.STATUS_CANCELLED,
        )

        today = date.today()
        current_coverage = all_coverage.filter(start_date__lte=today, end_date__gte=today)
        current_licenses = all_licenses.filter(
            billing_term='subscription', start_date__lte=today, end_date__gte=today,
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


class CoverageListButton(PluginTemplateExtension):
    """'Add to Support Contract' button on the core Device and Module list pages."""
    models = ['dcim.device', 'dcim.module']

    def list_buttons(self):
        request = self.context['request']
        if not request.user.has_perm('netbox_tco.change_coverageline'):
            return ''
        model_name = self.context['object']._meta.model_name
        return self.render('netbox_tco/inc/coverage_list_button.html', extra_context={
            'assign_url': reverse('plugins:netbox_tco:coverageline_assign', kwargs={'model_name': model_name}),
        })


class DeviceEOLPanel(PluginTemplateExtension):
    """Adds EOS/EOL milestone table to Device detail page."""
    models = ['dcim.device']

    def left_page(self):
        device = self.context['object']
        from .models import LifecycleRecord

        try:
            record = LifecycleRecord.objects.prefetch_related('milestones').get(
                device_types=device.device_type
            )
            milestones = record.milestones.order_by('date')
        except LifecycleRecord.DoesNotExist:
            record = None
            milestones = []

        return self.render('netbox_tco/inc/device_eol.html', extra_context={
            'lifecycle_record': record,
            'milestones': milestones,
            'today': date.today(),
        })


template_extensions = [DeviceTCOPanel, DeviceEOLPanel, CoverageListButton]
