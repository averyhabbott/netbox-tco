from datetime import date
from decimal import Decimal

from dcim.models import Device, Module
from django.apps import apps
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Count, Max, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.dateparse import parse_date
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from netbox.object_actions import AddObject, BulkDelete, BulkEdit, BulkExport, DeleteObject, EditObject
from netbox.views.generic import (
    BulkDeleteView, BulkEditView, ObjectChildrenView, ObjectDeleteView, ObjectEditView,
    ObjectListView, ObjectView,
)
from utilities.views import ViewTab, register_model_view

from .choices import BillingTermChoices, ContractStatusChoices, CoverageStatusChoices, LineItemTypeChoices
from .provisioning import coverable_limit_choices_to, coverable_model_names

from .filtersets import (
    CoverageLineFilterSet, LicenseFilterSet, LicenseLineFilterSet, LicenseTypeFilterSet, LifecycleRecordFilterSet,
    LineItemFilterSet, MilestoneTypeFilterSet, QPIFilterSet, ServiceLevelFilterSet, SupportContractFilterSet,
)
from .forms import (
    AddToContractForm, AddToLicenseForm, AddToSupportContractForm, AttachmentForm, CoverageLineBulkEditForm,
    CoverageLineFilterForm, CoverageLineForm, LicenseFilterForm, LicenseForm, LicenseLineBulkEditForm,
    LicenseLineFilterForm, LicenseLineForm,
    LicensePartNumberForm, LicenseTypeForm, LicenseTypeFilterForm,
    LifecycleRecordForm, LifecycleRecordFilterForm, LifecycleMilestoneForm,
    LineItemForm, LineItemFilterForm, MilestoneTypeForm, MilestoneTypeFilterForm, QPIForm, QPIFilterForm,
    ServiceLevelForm, ServiceLevelFilterForm, ServiceLevelPartNumberForm,
    SupportContractForm, SupportContractFilterForm,
)
from .models import (
    Attachment, CoverageLine, License, LicenseLine, LicensePartNumber, LicenseType,
    LifecycleMilestone, LifecycleRecord, LineItem, MilestoneType, ProvisionedItem, QPI, ServiceLevel,
    ServiceLevelPartNumber, SupportContract,
)
from .tables import (
    CoverageLineTable, LicenseLineTable, LicenseTable, LicenseTypeTable, LifecycleRecordTable,
    LineItemTable, MilestoneTypeTable, QPITable, ServiceLevelTable, SupportContractTable,
)


# ---------------------------------------------------------------------------
# Service Levels
# ---------------------------------------------------------------------------

@register_model_view(ServiceLevel, 'list', path='', detail=False)
class ServiceLevelListView(ObjectListView):
    queryset = ServiceLevel.objects.prefetch_related('part_numbers').annotate(
        part_number_count=Count('part_numbers')
    )
    table = ServiceLevelTable
    filterset = ServiceLevelFilterSet
    filterset_form = ServiceLevelFilterForm


@register_model_view(ServiceLevel)
class ServiceLevelView(ObjectView):
    queryset = ServiceLevel.objects.prefetch_related('part_numbers__manufacturer')

    def get_extra_context(self, request, instance):
        return {'part_numbers': instance.part_numbers.select_related('manufacturer')}


@register_model_view(ServiceLevel, 'add', detail=False)
@register_model_view(ServiceLevel, 'edit')
class ServiceLevelEditView(ObjectEditView):
    queryset = ServiceLevel.objects.all()
    form = ServiceLevelForm


@register_model_view(ServiceLevel, 'delete')
class ServiceLevelDeleteView(ObjectDeleteView):
    queryset = ServiceLevel.objects.all()


# ---------------------------------------------------------------------------
# License Types
# ---------------------------------------------------------------------------

@register_model_view(LicenseType, 'list', path='', detail=False)
class LicenseTypeListView(ObjectListView):
    queryset = LicenseType.objects.prefetch_related('part_numbers').annotate(
        part_number_count=Count('part_numbers')
    )
    table = LicenseTypeTable
    filterset = LicenseTypeFilterSet
    filterset_form = LicenseTypeFilterForm


@register_model_view(LicenseType)
class LicenseTypeView(ObjectView):
    queryset = LicenseType.objects.prefetch_related('part_numbers__manufacturer')

    def get_extra_context(self, request, instance):
        return {'part_numbers': instance.part_numbers.select_related('manufacturer')}


@register_model_view(LicenseType, 'add', detail=False)
@register_model_view(LicenseType, 'edit')
class LicenseTypeEditView(ObjectEditView):
    queryset = LicenseType.objects.all()
    form = LicenseTypeForm


@register_model_view(LicenseType, 'delete')
class LicenseTypeDeleteView(ObjectDeleteView):
    queryset = LicenseType.objects.all()


# ---------------------------------------------------------------------------
# Part Numbers — Service Level
# ---------------------------------------------------------------------------

class ServiceLevelPartNumberCreateView(PermissionRequiredMixin, View):
    permission_required = 'netbox_tco.add_servicelevelpartnumber'

    def get(self, request, sl_pk):
        service_level = get_object_or_404(ServiceLevel, pk=sl_pk)
        form = ServiceLevelPartNumberForm()
        return render(request, 'netbox_tco/partnumber_edit.html', {
            'object': service_level,
            'form': form,
            'title': f'Add Part Number — {service_level}',
            'cancel_url': service_level.get_absolute_url(),
        })

    def post(self, request, sl_pk):
        service_level = get_object_or_404(ServiceLevel, pk=sl_pk)
        form = ServiceLevelPartNumberForm(request.POST)
        if form.is_valid():
            pn = form.save(commit=False)
            pn.service_level = service_level
            pn.save()
            messages.success(request, f'Added part number {pn.part_number}.')
            return redirect(service_level.get_absolute_url())
        return render(request, 'netbox_tco/partnumber_edit.html', {
            'object': service_level,
            'form': form,
            'title': f'Add Part Number — {service_level}',
            'cancel_url': service_level.get_absolute_url(),
        })


class ServiceLevelPartNumberEditView(PermissionRequiredMixin, View):
    permission_required = 'netbox_tco.change_servicelevelpartnumber'

    def get(self, request, pk):
        pn = get_object_or_404(ServiceLevelPartNumber, pk=pk)
        form = ServiceLevelPartNumberForm(instance=pn)
        return render(request, 'netbox_tco/partnumber_edit.html', {
            'object': pn.service_level,
            'form': form,
            'title': f'Edit Part Number — {pn.part_number}',
            'cancel_url': pn.service_level.get_absolute_url(),
        })

    def post(self, request, pk):
        pn = get_object_or_404(ServiceLevelPartNumber, pk=pk)
        form = ServiceLevelPartNumberForm(request.POST, instance=pn)
        if form.is_valid():
            form.save()
            messages.success(request, f'Updated part number {pn.part_number}.')
            return redirect(pn.service_level.get_absolute_url())
        return render(request, 'netbox_tco/partnumber_edit.html', {
            'object': pn.service_level,
            'form': form,
            'title': f'Edit Part Number — {pn.part_number}',
            'cancel_url': pn.service_level.get_absolute_url(),
        })


class ServiceLevelPartNumberDeleteView(PermissionRequiredMixin, View):
    permission_required = 'netbox_tco.delete_servicelevelpartnumber'

    def get(self, request, pk):
        pn = get_object_or_404(ServiceLevelPartNumber, pk=pk)
        return render(request, 'netbox_tco/partnumber_confirm_delete.html', {
            'object': pn.service_level,
            'target': pn,
            'cancel_url': pn.service_level.get_absolute_url(),
        })

    def post(self, request, pk):
        pn = get_object_or_404(ServiceLevelPartNumber, pk=pk)
        service_level = pn.service_level
        pn.delete()
        messages.success(request, f'Deleted part number {pn.part_number}.')
        return redirect(service_level.get_absolute_url())


# ---------------------------------------------------------------------------
# Part Numbers — License Type
# ---------------------------------------------------------------------------

class LicensePartNumberCreateView(PermissionRequiredMixin, View):
    permission_required = 'netbox_tco.add_licensepartnumber'

    def get(self, request, lt_pk):
        license_type = get_object_or_404(LicenseType, pk=lt_pk)
        form = LicensePartNumberForm()
        return render(request, 'netbox_tco/partnumber_edit.html', {
            'object': license_type,
            'form': form,
            'title': f'Add Part Number — {license_type}',
            'cancel_url': license_type.get_absolute_url(),
        })

    def post(self, request, lt_pk):
        license_type = get_object_or_404(LicenseType, pk=lt_pk)
        form = LicensePartNumberForm(request.POST)
        if form.is_valid():
            pn = form.save(commit=False)
            pn.license_type = license_type
            pn.save()
            messages.success(request, f'Added part number {pn.part_number}.')
            return redirect(license_type.get_absolute_url())
        return render(request, 'netbox_tco/partnumber_edit.html', {
            'object': license_type,
            'form': form,
            'title': f'Add Part Number — {license_type}',
            'cancel_url': license_type.get_absolute_url(),
        })


class LicensePartNumberEditView(PermissionRequiredMixin, View):
    permission_required = 'netbox_tco.change_licensepartnumber'

    def get(self, request, pk):
        pn = get_object_or_404(LicensePartNumber, pk=pk)
        form = LicensePartNumberForm(instance=pn)
        return render(request, 'netbox_tco/partnumber_edit.html', {
            'object': pn.license_type,
            'form': form,
            'title': f'Edit Part Number — {pn.part_number}',
            'cancel_url': pn.license_type.get_absolute_url(),
        })

    def post(self, request, pk):
        pn = get_object_or_404(LicensePartNumber, pk=pk)
        form = LicensePartNumberForm(request.POST, instance=pn)
        if form.is_valid():
            form.save()
            messages.success(request, f'Updated part number {pn.part_number}.')
            return redirect(pn.license_type.get_absolute_url())
        return render(request, 'netbox_tco/partnumber_edit.html', {
            'object': pn.license_type,
            'form': form,
            'title': f'Edit Part Number — {pn.part_number}',
            'cancel_url': pn.license_type.get_absolute_url(),
        })


class LicensePartNumberDeleteView(PermissionRequiredMixin, View):
    permission_required = 'netbox_tco.delete_licensepartnumber'

    def get(self, request, pk):
        pn = get_object_or_404(LicensePartNumber, pk=pk)
        return render(request, 'netbox_tco/partnumber_confirm_delete.html', {
            'object': pn.license_type,
            'target': pn,
            'cancel_url': pn.license_type.get_absolute_url(),
        })

    def post(self, request, pk):
        pn = get_object_or_404(LicensePartNumber, pk=pk)
        license_type = pn.license_type
        pn.delete()
        messages.success(request, f'Deleted part number {pn.part_number}.')
        return redirect(license_type.get_absolute_url())


# ---------------------------------------------------------------------------
# Attachments
# ---------------------------------------------------------------------------

class AttachmentCreateView(PermissionRequiredMixin, View):
    """Add an attachment to a parent object; subclasses set parent_model."""
    permission_required = 'netbox_tco.add_attachment'
    parent_model = QPI

    def _render(self, request, parent, form):
        return render(request, 'netbox_tco/attachment_edit.html', {
            'object': parent,
            'form': form,
            'title': f'Add Attachment — {parent}',
            'cancel_url': parent.get_absolute_url(),
        })

    def get(self, request, parent_pk):
        parent = get_object_or_404(self.parent_model, pk=parent_pk)
        return self._render(request, parent, AttachmentForm())

    def post(self, request, parent_pk):
        parent = get_object_or_404(self.parent_model, pk=parent_pk)
        form = AttachmentForm(request.POST, request.FILES)
        if form.is_valid():
            att = form.save(commit=False)
            att.content_type = ContentType.objects.get_for_model(self.parent_model)
            att.object_id = parent.pk
            att.uploaded_by = request.user
            att.save()
            messages.success(request, f'Added attachment {att.name}.')
            return redirect(parent.get_absolute_url())
        return self._render(request, parent, form)


class SupportContractAttachmentCreateView(AttachmentCreateView):
    parent_model = SupportContract


class LicenseAttachmentCreateView(AttachmentCreateView):
    parent_model = License


class LifecycleRecordAttachmentCreateView(AttachmentCreateView):
    parent_model = LifecycleRecord


class AttachmentEditView(PermissionRequiredMixin, View):
    permission_required = 'netbox_tco.change_attachment'

    def get(self, request, pk):
        att = get_object_or_404(Attachment, pk=pk)
        form = AttachmentForm(instance=att)
        parent = att.parent
        return render(request, 'netbox_tco/attachment_edit.html', {
            'object': parent,
            'form': form,
            'title': f'Edit Attachment — {att.name}',
            'cancel_url': parent.get_absolute_url(),
        })

    def post(self, request, pk):
        att = get_object_or_404(Attachment, pk=pk)
        form = AttachmentForm(request.POST, request.FILES, instance=att)
        parent = att.parent
        if form.is_valid():
            updated = form.save(commit=False)
            if not request.FILES.get('file'):
                updated.file = att.file
            updated.save()
            messages.success(request, f'Updated attachment {att.name}.')
            return redirect(parent.get_absolute_url())
        return render(request, 'netbox_tco/attachment_edit.html', {
            'object': parent,
            'form': form,
            'title': f'Edit Attachment — {att.name}',
            'cancel_url': parent.get_absolute_url(),
        })


class AttachmentDeleteView(PermissionRequiredMixin, View):
    permission_required = 'netbox_tco.delete_attachment'

    def get(self, request, pk):
        att = get_object_or_404(Attachment, pk=pk)
        return render(request, 'netbox_tco/attachment_confirm_delete.html', {
            'object': att.parent,
            'target': att,
            'cancel_url': att.parent.get_absolute_url(),
        })

    def post(self, request, pk):
        att = get_object_or_404(Attachment, pk=pk)
        parent = att.parent
        name = att.name
        att.delete()
        messages.success(request, f'Deleted attachment {name}.')
        return redirect(parent.get_absolute_url())


# ---------------------------------------------------------------------------
# QPIs
# ---------------------------------------------------------------------------

@register_model_view(QPI, 'list', path='', detail=False)
class QPIListView(ObjectListView):
    queryset = QPI.objects.prefetch_related('owners')
    table = QPITable
    filterset = QPIFilterSet
    filterset_form = QPIFilterForm


@register_model_view(QPI)
class QPIView(ObjectView):
    queryset = QPI.objects.prefetch_related('owners', 'line_items')

    def get_extra_context(self, request, instance):
        from django.contrib.contenttypes.models import ContentType
        ct = ContentType.objects.get_for_model(QPI)
        line_items = list(instance.line_items.select_related(
            'device_type',
            'support_sku__manufacturer', 'support_sku__service_level',
            'license_sku__manufacturer', 'license_sku__license_type',
        ))
        return {
            'line_items': line_items,
            'qpi_total': sum(li.line_total for li in line_items),
            'attachments': Attachment.objects.filter(
                content_type=ct, object_id=instance.pk
            ).select_related('uploaded_by'),
        }


@register_model_view(QPI, 'add', detail=False)
@register_model_view(QPI, 'edit')
class QPIEditView(ObjectEditView):
    queryset = QPI.objects.all()
    form = QPIForm


@register_model_view(QPI, 'delete')
class QPIDeleteView(ObjectDeleteView):
    queryset = QPI.objects.all()


# ---------------------------------------------------------------------------
# Line Items
# ---------------------------------------------------------------------------

@register_model_view(LineItem, 'list', path='', detail=False)
class LineItemListView(ObjectListView):
    queryset = LineItem.objects.select_related('qpi', 'device_type', 'support_sku', 'license_sku')
    table = LineItemTable
    filterset = LineItemFilterSet
    filterset_form = LineItemFilterForm


@register_model_view(LineItem)
class LineItemView(ObjectView):
    queryset = LineItem.objects.select_related(
        'qpi', 'device_type', 'module_type', 'rack_type',
        'support_sku__manufacturer', 'support_sku__service_level',
        'license_sku__manufacturer', 'license_sku__license_type',
    )

    def get_extra_context(self, request, instance):
        from django.apps import apps
        from django.contrib.contenttypes.models import ContentType
        from django.urls import reverse
        from urllib.parse import urlencode
        from .provisioning import entry_for_line_item

        raw_pis = list(instance.provisioned_items.select_related('content_type'))
        back_url = instance.get_absolute_url()

        provisioned_items = []
        for pi in raw_pis:
            target = pi.target  # resolves GenericFK
            delete_url = None
            if target:
                try:
                    delete_path = reverse(
                        f'dcim:{pi.content_type.model}_delete',
                        kwargs={'pk': target.pk},
                    )
                    delete_url = f'{delete_path}?return_url={back_url}'
                except Exception:
                    pass
            provisioned_items.append({
                'pi': pi,
                'target': target,
                'delete_url': delete_url,
            })

        # Determine hardware model and remaining count via registry
        type_entry = entry_for_line_item(instance)
        hw_model = apps.get_model(type_entry['model']) if type_entry else None

        remaining = 0
        provision_url = None
        if hw_model and instance.line_type == 'hardware':
            ct = ContentType.objects.get_for_model(hw_model)
            provisioned_count = instance.provisioned_items.filter(content_type=ct).count()
            remaining = max(0, instance.quantity - provisioned_count)

            if remaining > 0:
                type_fk_value = getattr(instance, type_entry['line_item_fk'])
                params = {
                    type_entry['line_item_fk']: type_fk_value.pk,
                    'cf_tco_line_item': instance.pk,
                    'return_url': back_url,
                }
                provision_url = f'{type_entry["add_url"]}?{urlencode(params)}'

        funded_lines = []
        lines_remaining = 0
        if instance.line_type in (LineItemTypeChoices.TYPE_SUPPORT, LineItemTypeChoices.TYPE_LICENSE):
            line_model = CoverageLine if instance.line_type == LineItemTypeChoices.TYPE_SUPPORT else LicenseLine
            funded_lines = list(
                line_model.objects.filter(funding_line_item=instance)
                .select_related(line_model.parent_attr, 'assigned_object_type')
                .prefetch_related('assigned_object')
                .order_by(f'{line_model.parent_attr}__name', 'pk')
            )
            lines_remaining = max(0, instance.quantity - len(funded_lines))

        return {
            'provisioned_items': provisioned_items,
            'remaining': remaining,
            'provision_url': provision_url,
            'funded_lines': funded_lines,
            'lines_remaining': lines_remaining,
        }


class ProvisionedItemBulkRemoveView(PermissionRequiredMixin, View):
    """Unlink selected ProvisionedItems from a line item (does not delete the objects)."""
    permission_required = 'netbox_tco.delete_provisioneditem'

    def post(self, request):
        pk_list = [int(pk) for pk in request.POST.getlist('pk') if pk.isdigit()]
        return_url = request.POST.get('return_url', '/')

        if not pk_list:
            messages.warning(request, 'No items selected.')
            return redirect(return_url)

        pis = list(ProvisionedItem.objects.filter(pk__in=pk_list).select_related('content_type'))
        targets = [(pi.content_type, pi.object_id, pi.target) for pi in pis]

        # Delete junction records first so the save signal below is a no-op
        ProvisionedItem.objects.filter(pk__in=pk_list).delete()

        # Clear the custom field on each target so the UI stays consistent
        for _ct, _obj_id, target in targets:
            if target and hasattr(target, 'custom_field_data'):
                target.custom_field_data['tco_line_item'] = None
                target.save()

        messages.success(request, f'Removed {len(pis)} item(s) from line item.')
        return redirect(return_url)


class ProvisionedItemBulkDeleteView(PermissionRequiredMixin, View):
    """Delete the actual objects (Device/Module/Rack) referenced by selected ProvisionedItems."""
    permission_required = 'netbox_tco.delete_provisioneditem'

    def get(self, request):
        return redirect(request.GET.get('return_url', '/'))

    def post(self, request):
        pk_list = [int(pk) for pk in request.POST.getlist('pk') if pk.isdigit()]
        return_url = request.POST.get('return_url', '/')

        if not pk_list:
            messages.warning(request, 'No items selected.')
            return redirect(return_url)

        if '_confirm' in request.POST:
            pis = list(ProvisionedItem.objects.filter(pk__in=pk_list).select_related('content_type'))
            count = 0
            for pi in pis:
                target = pi.target
                if target:
                    target.delete()  # pre_delete signal cleans up the ProvisionedItem
                    count += 1
                else:
                    pi.delete()
            messages.success(request, f'Deleted {count} object(s).')
            return redirect(return_url)

        # Show confirmation page
        pis = list(ProvisionedItem.objects.filter(pk__in=pk_list).select_related('content_type'))
        items = [{'pi': pi, 'target': pi.target} for pi in pis]
        return render(request, 'netbox_tco/provisioned_item_bulk_delete.html', {
            'items': items,
            'pk_list': pk_list,
            'return_url': return_url,
        })


@register_model_view(LineItem, 'add', detail=False)
@register_model_view(LineItem, 'edit')
class LineItemEditView(ObjectEditView):
    queryset = LineItem.objects.all()
    form = LineItemForm


@register_model_view(LineItem, 'delete')
class LineItemDeleteView(ObjectDeleteView):
    queryset = LineItem.objects.all()


# ---------------------------------------------------------------------------
# Support Contracts & Licenses — shared helpers
# ---------------------------------------------------------------------------

def _contract_context(request, instance):
    """Detail-page context shared by Support Contract and License (template: contract.html)."""
    is_license = isinstance(instance, License)
    line_model = LicenseLine if is_license else CoverageLine
    line_name = line_model._meta.model_name
    back = instance.get_absolute_url()
    lines = list(
        instance.lines.select_related(
            'funding_line_item__qpi', 'assigned_object_type', 'license_type' if is_license else 'service_level',
        ).prefetch_related('assigned_object')
    )
    lines.sort(key=lambda l: (
        -(l.end_date or date.max).toordinal(), -l.start_date.toordinal(), str(l.assigned_object or ''), l.pk,
    ))
    status_counts = {}
    for line in lines:
        status_counts[line.get_status_display()] = status_counts.get(line.get_status_display(), 0) + 1
    start = min((l.start_date for l in lines), default=None)
    end = max((l.end_date for l in lines if l.end_date), default=None)
    return {
        'is_license': is_license,
        'noun': instance._meta.verbose_name,
        'reference_label': instance._meta.get_field(instance.reference_attr).verbose_name.capitalize(),
        'reference': getattr(instance, instance.reference_attr),
        'lines_label': 'Line Items',
        'line_add_url': (f'{reverse(f"plugins:netbox_tco:{line_name}_add")}'
                         f'?{line_model.parent_attr}={instance.pk}&return_url={back}'),
        'line_bulk_edit_url': reverse(f'plugins:netbox_tco:{line_name}_bulk_edit'),
        'line_bulk_delete_url': reverse(f'plugins:netbox_tco:{line_name}_bulk_delete'),
        'can_add_line': request.user.has_perm(f'netbox_tco.add_{line_name}'),
        'can_change_line': request.user.has_perm(f'netbox_tco.change_{line_name}'),
        'can_delete_line': request.user.has_perm(f'netbox_tco.delete_{line_name}'),
        'lines': lines,
        'status_counts': status_counts,
        'contract_start': start,
        'contract_end': end,
        'is_expired': end is not None and end < date.today(),
        'contract_total': sum((l.price for l in lines), Decimal('0')),
        'funding_line_items': instance.funding_line_items.select_related('qpi'),
        'attachments': Attachment.objects.filter(
            content_type=ContentType.objects.get_for_model(instance), object_id=instance.pk,
        ).select_related('uploaded_by'),
        'attachment_add_url': reverse(
            f'plugins:netbox_tco:{instance._meta.model_name}_attachment_add', kwargs={'parent_pk': instance.pk},
        ),
    }


def _overlapping_keys(contract, start, end):
    """
    Objects already assigned on `contract` with a line overlapping start..end; touching ends don't
    count. An end of None (perpetual) is open-ended on either side.
    """
    lines = contract.lines.filter(status=CoverageStatusChoices.STATUS_ASSIGNED)
    if end is not None:
        lines = lines.filter(start_date__lt=end)
    lines = lines.filter(Q(end_date__isnull=True) | Q(end_date__gt=start))
    return set(lines.values_list('assigned_object_type_id', 'assigned_object_id'))


def _new_line(line_model, contract, line_item, **values):
    line = line_model(**{line_model.parent_attr: contract}, funding_line_item=line_item, **values)
    line.apply_funding_defaults()
    return line


def _fill_lines(contract, objects, ct, pending, make_line=None, free=0):
    """
    Assign `objects` to `pending` lines (in order), then to up to `free` new lines from
    make_line(). Objects already on the contract for overlapping dates are skipped.
    Returns (assigned_count, skipped_objects).
    """
    pending = list(pending)
    assigned, skipped = 0, []
    for obj in objects:
        if pending:
            line = pending[0]
        elif free > 0:
            line = make_line()
        else:
            skipped.append(obj)
            continue
        if (ct.pk, obj.pk) in _overlapping_keys(contract, line.start_date, line.end_date):
            skipped.append(obj)
            continue
        if line.pk:
            pending.pop(0)
            line.snapshot()
        else:
            free -= 1
        line.assigned_object = obj
        line.save()
        assigned += 1
    return assigned, skipped


def _skipped_message(skipped):
    names = ', '.join(str(o) for o in skipped[:10]) + ('…' if len(skipped) > 10 else '')
    return f'Skipped {len(skipped)} already on it for overlapping dates: {names}'


# ---------------------------------------------------------------------------
# Support Contracts
# ---------------------------------------------------------------------------

@register_model_view(SupportContract, 'list', path='', detail=False)
class SupportContractListView(ObjectListView):
    queryset = SupportContract.objects.select_related('vendor').annotate(
        line_count=Count('coverage_lines'),
        latest_end=Max('coverage_lines__end_date'),
    )
    table = SupportContractTable
    filterset = SupportContractFilterSet
    filterset_form = SupportContractFilterForm


@register_model_view(SupportContract)
class SupportContractView(ObjectView):
    queryset = SupportContract.objects.select_related('vendor').prefetch_related(
        'predecessors', 'successors',
    )

    template_name = 'netbox_tco/contract.html'

    def get_extra_context(self, request, instance):
        return _contract_context(request, instance)


@register_model_view(SupportContract, 'add', detail=False)
@register_model_view(SupportContract, 'edit')
class SupportContractEditView(ObjectEditView):
    queryset = SupportContract.objects.all()
    form = SupportContractForm


@register_model_view(SupportContract, 'delete')
class SupportContractDeleteView(ObjectDeleteView):
    queryset = SupportContract.objects.all()


# ---------------------------------------------------------------------------
# Coverage Lines
# ---------------------------------------------------------------------------

COVERAGE_LINE_QS = CoverageLine.objects.select_related(
    'support_contract', 'service_level', 'funding_line_item', 'assigned_object_type',
).prefetch_related('assigned_object', 'tags')


@register_model_view(CoverageLine, 'list', path='', detail=False)
class CoverageLineListView(ObjectListView):
    queryset = COVERAGE_LINE_QS
    table = CoverageLineTable
    filterset = CoverageLineFilterSet
    filterset_form = CoverageLineFilterForm
    actions = (AddObject, BulkExport, BulkEdit, BulkDelete)


@register_model_view(CoverageLine)
class CoverageLineView(ObjectView):
    queryset = COVERAGE_LINE_QS


@register_model_view(CoverageLine, 'add', detail=False)
@register_model_view(CoverageLine, 'edit')
class CoverageLineEditView(ObjectEditView):
    queryset = CoverageLine.objects.all()
    form = CoverageLineForm


@register_model_view(CoverageLine, 'delete')
class CoverageLineDeleteView(ObjectDeleteView):
    queryset = CoverageLine.objects.all()


@register_model_view(CoverageLine, 'bulk_edit', path='edit', detail=False)
class CoverageLineBulkEditView(BulkEditView):
    queryset = COVERAGE_LINE_QS
    filterset = CoverageLineFilterSet
    table = CoverageLineTable
    form = CoverageLineBulkEditForm


@register_model_view(CoverageLine, 'bulk_delete', path='delete', detail=False)
class CoverageLineBulkDeleteView(BulkDeleteView):
    queryset = COVERAGE_LINE_QS
    filterset = CoverageLineFilterSet
    table = CoverageLineTable


# ---------------------------------------------------------------------------
# Licenses
# ---------------------------------------------------------------------------

@register_model_view(License, 'list', path='', detail=False)
class LicenseListView(ObjectListView):
    queryset = License.objects.select_related('vendor').annotate(
        line_count=Count('license_lines'),
        latest_end=Max('license_lines__end_date'),
    )
    table = LicenseTable
    filterset = LicenseFilterSet
    filterset_form = LicenseFilterForm


@register_model_view(License)
class LicenseView(ObjectView):
    queryset = License.objects.select_related('vendor').prefetch_related(
        'predecessors', 'successors',
    )

    template_name = 'netbox_tco/contract.html'

    def get_extra_context(self, request, instance):
        return _contract_context(request, instance)


@register_model_view(License, 'add', detail=False)
@register_model_view(License, 'edit')
class LicenseEditView(ObjectEditView):
    queryset = License.objects.all()
    form = LicenseForm


@register_model_view(License, 'delete')
class LicenseDeleteView(ObjectDeleteView):
    queryset = License.objects.all()


# ---------------------------------------------------------------------------
# License Lines
# ---------------------------------------------------------------------------

LICENSE_LINE_QS = LicenseLine.objects.select_related(
    'license', 'license_type', 'funding_line_item', 'assigned_object_type',
).prefetch_related('assigned_object', 'tags')


@register_model_view(LicenseLine, 'list', path='', detail=False)
class LicenseLineListView(ObjectListView):
    queryset = LICENSE_LINE_QS
    table = LicenseLineTable
    filterset = LicenseLineFilterSet
    filterset_form = LicenseLineFilterForm
    actions = (AddObject, BulkExport, BulkEdit, BulkDelete)


@register_model_view(LicenseLine)
class LicenseLineView(ObjectView):
    queryset = LICENSE_LINE_QS


@register_model_view(LicenseLine, 'add', detail=False)
@register_model_view(LicenseLine, 'edit')
class LicenseLineEditView(ObjectEditView):
    queryset = LicenseLine.objects.all()
    form = LicenseLineForm


@register_model_view(LicenseLine, 'delete')
class LicenseLineDeleteView(ObjectDeleteView):
    queryset = LicenseLine.objects.all()


@register_model_view(LicenseLine, 'bulk_edit', path='edit', detail=False)
class LicenseLineBulkEditView(BulkEditView):
    queryset = LICENSE_LINE_QS
    filterset = LicenseLineFilterSet
    table = LicenseLineTable
    form = LicenseLineBulkEditForm


@register_model_view(LicenseLine, 'bulk_delete', path='delete', detail=False)
class LicenseLineBulkDeleteView(BulkDeleteView):
    queryset = LICENSE_LINE_QS
    filterset = LicenseLineFilterSet
    table = LicenseLineTable


# ---------------------------------------------------------------------------
# "Add to Support Contract" / "Add to License" (from a line item)
# ---------------------------------------------------------------------------

class AddToContractView(PermissionRequiredMixin, View):
    """Create lines on a new or existing contract/License, funded by one support/license line item."""
    template_name = 'netbox_tco/lineitem_add_to_contract.html'
    form_class = None
    line_model = None

    @property
    def contract_model(self):
        return self.form_class.contract_model

    def _get_line_item(self, pk):
        sku = self.line_model.sku_attr
        return get_object_or_404(
            LineItem.objects.select_related('qpi', f'{sku}__manufacturer'),
            pk=pk, line_type=self.line_model.funding_line_type,
        )

    def _remaining(self, line_item):
        return line_item.quantity - self.line_model.objects.filter(funding_line_item=line_item).count()

    def _render(self, request, line_item, form, remaining):
        return render(request, self.template_name, {
            'object': line_item,
            'form': form,
            'remaining': remaining,
            'noun': self.form_class.noun,
            'title': f'Add to {self.contract_model._meta.verbose_name.title()}',
            'is_license': self.contract_model is License,
            'return_url': line_item.get_absolute_url(),
        })

    def get(self, request, pk):
        line_item = self._get_line_item(pk)
        remaining = self._remaining(line_item)
        if remaining <= 0:
            messages.warning(request, 'Every unit on this line item is already on a line.')
            return redirect(line_item.get_absolute_url())
        sku = getattr(line_item, self.line_model.sku_attr)
        initial = {
            'mode': AddToContractForm.MODE_NEW,
            'name': line_item.name or str(sku),
            'vendor': sku.manufacturer,
            'seed': AddToContractForm.SEED_PENDING,
            'start_date': line_item.start_date,
            'end_date': line_item.end_date,
            'price': line_item.unit_price,
            'billing_term': (BillingTermChoices.TERM_SUBSCRIPTION if line_item.term_months
                             else BillingTermChoices.TERM_PERPETUAL),
        }
        contract_pk = request.GET.get('contract')
        if contract_pk and contract_pk.isdigit():
            initial['mode'] = AddToContractForm.MODE_EXISTING
            initial['existing_contract'] = contract_pk
        form = self.form_class(initial=initial, line_item=line_item)
        return self._render(request, line_item, form, remaining)

    def post(self, request, pk):
        line_item = self._get_line_item(pk)
        remaining = self._remaining(line_item)
        form = self.form_class(request.POST, line_item=line_item)
        if not form.is_valid():
            return self._render(request, line_item, form, remaining)

        cd = form.cleaned_data
        start, end, price = cd['start_date'], cd['end_date'], cd['price']
        target = cd['existing_contract'] if cd['mode'] == form.MODE_EXISTING else None

        # Objects to cover, in order, as (content_type_id, object_id)
        coverable_ct_ids = set(
            ContentType.objects.filter(coverable_limit_choices_to()).values_list('pk', flat=True)
        )
        candidates = []
        if cd['seed'] == form.SEED_QPI:
            candidates = list(
                ProvisionedItem.objects.filter(
                    line_item__in=cd['source_line_items'],
                    content_type_id__in=coverable_ct_ids,
                ).order_by('content_type_id', 'object_id').values_list('content_type_id', 'object_id')
            )
        elif cd['seed'] == form.SEED_CONTRACT:
            source = form.get_source_contract()
            candidates = list(
                source.lines.filter(status=CoverageStatusChoices.STATUS_ASSIGNED)
                .order_by('assigned_object_type_id', 'assigned_object_id')
                .values_list('assigned_object_type_id', 'assigned_object_id').distinct()
            )

        if target is not None:
            already = _overlapping_keys(target, start, end)
            candidates = [c for c in candidates if c not in already]

        if len(candidates) > remaining:
            form.add_error(
                'seed',
                f'Found {len(candidates)} devices/modules to add, but this line item only has '
                f'{remaining} unit(s) left. Increase its quantity or pick "Blank pending lines".'
            )
            return self._render(request, line_item, form, remaining)

        with transaction.atomic():
            if target is None:
                target = self.contract_model(
                    name=cd['name'],
                    vendor=cd['vendor'],
                    status=(ContractStatusChoices.STATUS_PENDING if start > date.today()
                            else ContractStatusChoices.STATUS_ACTIVE),
                    **{self.contract_model.reference_attr: cd['reference']},
                )
                target.full_clean()
                target.save()
                target.predecessors.set(cd['predecessors'])

            values = dict(start_date=start, end_date=end, price=price)
            if 'billing_term' in cd:
                values['billing_term'] = cd['billing_term']
            for ct_id, obj_id in candidates:
                _new_line(self.line_model, target, line_item, assigned_object_type_id=ct_id,
                          assigned_object_id=obj_id, **values).save()
            pending = remaining - len(candidates)
            for _ in range(pending):
                _new_line(self.line_model, target, line_item, **values).save()
            target.apply_status_transitions()

        messages.success(
            request,
            f'Added {len(candidates)} assigned and {pending} pending line(s) to {target}.'
        )
        return redirect(target.get_absolute_url())


class AddToSupportContractView(AddToContractView):
    permission_required = ('netbox_tco.add_coverageline', 'netbox_tco.add_supportcontract')
    form_class = AddToSupportContractForm
    line_model = CoverageLine


class AddToLicenseView(AddToContractView):
    permission_required = ('netbox_tco.add_licenseline', 'netbox_tco.add_license')
    form_class = AddToLicenseForm
    line_model = LicenseLine


# ---------------------------------------------------------------------------
# "Attach TCO Item" (from the core Device / Module lists)
# ---------------------------------------------------------------------------

ATTACH_KINDS = {
    # type → (line model, contract model)
    LineItemTypeChoices.TYPE_SUPPORT: (CoverageLine, SupportContract),
    LineItemTypeChoices.TYPE_LICENSE: (LicenseLine, License),
}
NO_QPI = 'none'
NEW_TARGET = 'new'


class AttachTCOItemView(LoginRequiredMixin, View):
    """
    Attach devices/modules selected on a core list page to one exact TCO item: a hardware line
    item (source purchase), a support/license line item (on a chosen contract/License), or —
    with no QPI — straight to an existing contract's/License's pending lines.
    """
    template_name = 'netbox_tco/attach_tco_item.html'

    def _setup(self, request, model_name):
        if model_name not in coverable_model_names():
            raise Http404
        model = apps.get_model('dcim', model_name)
        pk_list = [int(pk) for pk in request.POST.getlist('pk') if pk.isdigit()]
        objects = list(model.objects.restrict(request.user, 'view').filter(pk__in=pk_list).order_by('pk'))
        return_url = request.POST.get('return_url') or reverse(f'dcim:{model_name}_list')
        if not url_has_allowed_host_and_scheme(return_url, allowed_hosts=None):
            return_url = reverse(f'dcim:{model_name}_list')
        return model, objects, return_url

    @staticmethod
    def _type_fk(model):
        return 'device_type' if model is Device else 'module_type'

    def _options(self, model, objects):
        """Every attachable item, for the page's QPI → Type → Item dropdowns."""
        type_fk = self._type_fk(model)
        items = []
        qpi_ids = set()

        # Hardware: only line items for the selected objects' device/module type(s)
        selected_types = {getattr(o, f'{type_fk}_id') for o in objects}
        hardware = LineItem.objects.filter(
            line_type=LineItemTypeChoices.TYPE_HARDWARE, **{f'{type_fk}__in': selected_types},
        ).select_related('qpi', type_fk).annotate(used=Count('provisioned_items'))
        for li in hardware:
            if li.used < li.quantity:
                items.append({
                    'value': f'li:{li.pk}', 'qpi': str(li.qpi_id), 'type': li.line_type, 'target': '',
                    'label': f'{li.name or getattr(li, type_fk)} — {li.quantity - li.used} of {li.quantity} remaining',
                })
                qpi_ids.add(li.qpi_id)

        targets = {}
        for line_type, (line_model, contract_model) in ATTACH_KINDS.items():
            related = contract_model.lines_attr
            for li in LineItem.objects.filter(line_type=line_type).select_related('qpi').annotate(
                used=Count(related),
                pending=Count(related, filter=Q(**{f'{related}__status': CoverageStatusChoices.STATUS_PENDING})),
            ):
                available = li.quantity - li.used + li.pending
                if available <= 0:
                    continue
                lines = line_model.objects.filter(funding_line_item=li)
                default = (lines.filter(status=CoverageStatusChoices.STATUS_PENDING).first() or lines.first())
                items.append({
                    'value': f'li:{li.pk}', 'qpi': str(li.qpi_id), 'type': line_type,
                    'target': str(default.parent.pk) if default else NEW_TARGET,
                    'name': li.name or str(getattr(li, line_model.sku_attr)),
                    'start': li.start_date.isoformat() if li.start_date else '',
                    'label': f'{li.name or getattr(li, line_model.sku_attr)} — {available} of {li.quantity} remaining',
                })
                qpi_ids.add(li.qpi_id)

            # No purchase record: contracts / licenses with pending lines
            for contract in contract_model.objects.annotate(pending=Count(
                related, filter=Q(**{f'{related}__status': CoverageStatusChoices.STATUS_PENDING}),
            )).filter(pending__gt=0):
                items.append({
                    'value': f'contract:{contract.pk}', 'qpi': NO_QPI, 'type': line_type, 'target': '',
                    'label': f'{contract} — {contract.pending} pending line{"s" if contract.pending != 1 else ""}',
                })
            targets[line_type] = [{'value': str(c.pk), 'label': str(c)} for c in contract_model.objects.all()]

        qpis = [{'value': NO_QPI, 'label': '(none)'}] + [
            {'value': str(q.pk), 'label': str(q)} for q in QPI.objects.filter(pk__in=qpi_ids).order_by('name')
        ]
        types = [{'value': v, 'label': l} for v, l, *_ in LineItemTypeChoices.CHOICES]
        return {'qpis': qpis, 'types': types, 'items': items, 'targets': targets,
                'today': date.today().isoformat()}

    def _render(self, request, model, objects, return_url, errors=()):
        provisioned = dict(
            ProvisionedItem.objects.filter(
                content_type=ContentType.objects.get_for_model(model), object_id__in=[o.pk for o in objects],
            ).select_related('line_item__qpi').values_list('object_id', 'line_item')
        )
        line_items = LineItem.objects.in_bulk(set(provisioned.values()))
        rows = [{'obj': o, 'source': line_items.get(provisioned.get(o.pk)),
                 'type': getattr(o, self._type_fk(model))} for o in objects]
        return render(request, self.template_name, {
            'rows': rows,
            'objects': objects,
            'model_name': model._meta.model_name,
            'verbose_name_plural': model._meta.verbose_name_plural,
            'return_url': return_url,
            'options': self._options(model, objects),
            'selected': {k: request.POST.get(k, '') for k in (
                'qpi', 'type', 'item', 'target', 'start_date', 'new_name', 'new_reference',
            )},
            'errors': errors,
        })

    def post(self, request, model_name):
        model, objects, return_url = self._setup(request, model_name)
        if not objects:
            messages.warning(request, f'No {model._meta.verbose_name_plural} selected.')
            return redirect(return_url)
        if '_confirm' not in request.POST:
            return self._render(request, model, objects, return_url)

        line_type = request.POST.get('type')
        kind, _, pk = request.POST.get('item', '').partition(':')
        try:
            if kind == 'li':
                line_item = LineItem.objects.select_related('qpi').get(pk=int(pk), line_type=line_type)
                if line_type == LineItemTypeChoices.TYPE_HARDWARE:
                    result = self._attach_hardware(request, model, objects, line_item)
                else:
                    result = self._attach_to_line_item(request, model, objects, line_item)
            elif kind == 'contract' and line_type in ATTACH_KINDS:
                line_model, contract_model = ATTACH_KINDS[line_type]
                contract = contract_model.objects.get(pk=int(pk))
                result = self._attach_to_contract(request, model, objects, contract, line_model)
            else:
                raise _AttachError('Choose an item to attach.')
        except (LineItem.DoesNotExist, SupportContract.DoesNotExist, License.DoesNotExist, ValueError):
            result = None
            errors = ['That item no longer exists. Choose another.']
        except _AttachError as e:
            result = None
            errors = e.messages
        if result is None:
            return self._render(request, model, objects, return_url, errors)
        return redirect(result)

    def _require(self, request, *perms):
        if not all(request.user.has_perm(p) for p in perms):
            raise _AttachError('You do not have permission to do that.')

    def _attach_hardware(self, request, model, objects, line_item):
        self._require(request, f'dcim.change_{model._meta.model_name}')
        type_fk = self._type_fk(model)
        wrong_type = [o for o in objects if getattr(o, f'{type_fk}_id') != getattr(line_item, f'{type_fk}_id')]
        if wrong_type:
            raise _AttachError(
                f'These are not a {getattr(line_item, type_fk) or "matching type"}: '
                + ', '.join(str(o) for o in wrong_type[:10])
            )
        ct = ContentType.objects.get_for_model(model)
        current = dict(ProvisionedItem.objects.filter(
            content_type=ct, object_id__in=[o.pk for o in objects],
        ).values_list('object_id', 'line_item_id'))
        elsewhere = [o for o in objects if current.get(o.pk) not in (None, line_item.pk)]
        if elsewhere:
            raise _AttachError(
                'Already attached to a different hardware line item (remove it there first): '
                + ', '.join(str(o) for o in elsewhere[:10])
            )
        new = [o for o in objects if o.pk not in current]
        remaining = line_item.quantity - line_item.provisioned_items.count()
        if len(new) > remaining:
            raise _AttachError(
                f'{len(new)} selected, but this line item only has {remaining} unit(s) left.'
            )
        allowed = set(model.objects.restrict(request.user, 'change').filter(
            pk__in=[o.pk for o in new]).values_list('pk', flat=True))
        if len(allowed) < len(new):
            raise _AttachError('You do not have permission to change some of the selected objects.')
        with transaction.atomic():
            for obj in new:
                obj.snapshot()
                obj.custom_field_data['tco_line_item'] = line_item.pk
                obj.save()  # post_save signal creates the ProvisionedItem
        messages.success(request, f'Attached {len(new)} {model._meta.verbose_name_plural} to {line_item}.')
        if len(new) < len(objects):
            messages.info(request, f'{len(objects) - len(new)} were already attached to it.')
        return line_item.get_absolute_url()

    def _attach_to_line_item(self, request, model, objects, line_item):
        line_model, contract_model = ATTACH_KINDS[line_item.line_type]
        noun = contract_model._meta.verbose_name
        target_value = request.POST.get('target', '')
        perms = [f'netbox_tco.add_{line_model._meta.model_name}', f'netbox_tco.change_{line_model._meta.model_name}']
        if target_value == NEW_TARGET:
            perms.append(f'netbox_tco.add_{contract_model._meta.model_name}')
        self._require(request, *perms)

        try:
            start = parse_date(request.POST.get('start_date', '').strip())
        except ValueError:
            start = None
        if start is None:
            raise _AttachError('Enter a valid start date.')
        probe = _new_line(line_model, None, line_item, start_date=start)
        if probe.has_end_date() and not probe.end_date and line_item.term_months:
            from dateutil.relativedelta import relativedelta
            probe.end_date = start + relativedelta(months=line_item.term_months)
        if probe.has_end_date() and not probe.end_date:
            raise _AttachError(f'Set a term on {line_item} first.')
        if probe.end_date and probe.end_date < start:
            raise _AttachError(f'The start date is after {line_item} ends ({probe.end_date}).')

        if target_value == NEW_TARGET:
            name = request.POST.get('new_name', '').strip()
            if not name:
                raise _AttachError(f'Name the new {noun}.')
            contract = None
        elif target_value.isdigit():
            contract = contract_model.objects.filter(pk=int(target_value)).first()
            if contract is None:
                raise _AttachError(f'Choose a {noun}.')
        else:
            raise _AttachError(f'Choose a {noun}.')

        ct = ContentType.objects.get_for_model(model)
        with transaction.atomic():
            pending, already = [], set()
            if contract is not None:
                pending = list(
                    contract.lines.select_for_update()
                    .filter(funding_line_item=line_item, status=CoverageStatusChoices.STATUS_PENDING)
                    .order_by('start_date', 'pk')
                )
                already = _overlapping_keys(contract, probe.start_date, probe.end_date)
            candidates = [o for o in objects if (ct.pk, o.pk) not in already]
            free = line_item.quantity - line_model.objects.filter(funding_line_item=line_item).count()
            if len(candidates) > len(pending) + free:
                raise _AttachError(
                    f'{len(candidates)} to add, but {line_item} only has {len(pending) + free} unit(s) left.'
                )
            if contract is None:
                sku = getattr(line_item, line_model.sku_attr)
                contract = contract_model(
                    name=name,
                    vendor=sku.manufacturer,
                    status=(ContractStatusChoices.STATUS_PENDING if probe.start_date > date.today()
                            else ContractStatusChoices.STATUS_ACTIVE),
                    **{contract_model.reference_attr: request.POST.get('new_reference', '').strip()},
                )
                contract.full_clean()
                contract.save()
            assigned, skipped = _fill_lines(
                contract, candidates, ct, pending,
                make_line=lambda: _new_line(line_model, contract, line_item,
                                            start_date=probe.start_date, end_date=probe.end_date),
                free=free,
            )
            contract.apply_status_transitions()

        skipped += [o for o in objects if (ct.pk, o.pk) in already]
        messages.success(request, f'Added {assigned} {model._meta.verbose_name_plural} to {contract}.')
        if skipped:
            messages.warning(request, _skipped_message(skipped))
        return contract.get_absolute_url()

    def _attach_to_contract(self, request, model, objects, contract, line_model):
        self._require(request, f'netbox_tco.change_{line_model._meta.model_name}')
        ct = ContentType.objects.get_for_model(model)
        with transaction.atomic():
            pending = list(
                contract.lines.select_for_update()
                .filter(status=CoverageStatusChoices.STATUS_PENDING)
                .order_by('start_date', 'pk')
            )
            if len(objects) > len(pending):
                raise _AttachError(f'{len(objects)} selected, but {contract} only has {len(pending)} pending line(s).')
            assigned, skipped = _fill_lines(contract, objects, ct, pending)
        messages.success(request, f'Added {assigned} {model._meta.verbose_name_plural} to {contract}.')
        if skipped:
            messages.warning(request, _skipped_message(skipped))
        return contract.get_absolute_url()


class _AttachError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.messages = [message]


# ---------------------------------------------------------------------------
# Support / Licenses tabs on Device and Module
# ---------------------------------------------------------------------------

class _LinesTabView(ObjectChildrenView):
    actions = (EditObject, DeleteObject, BulkEdit, BulkDelete)
    base_queryset = None

    def get_children(self, request, parent):
        ct = ContentType.objects.get_for_model(parent)
        return self.base_queryset.filter(assigned_object_type=ct, assigned_object_id=parent.pk)


def _lines_badge(line_model):
    def badge(obj):
        ct = ContentType.objects.get_for_model(obj)
        return line_model.objects.filter(assigned_object_type=ct, assigned_object_id=obj.pk).count()
    return badge


class _SupportTabView(_LinesTabView):
    child_model = CoverageLine
    table = CoverageLineTable
    filterset = CoverageLineFilterSet
    base_queryset = COVERAGE_LINE_QS


class _LicensesTabView(_LinesTabView):
    child_model = LicenseLine
    table = LicenseLineTable
    filterset = LicenseLineFilterSet
    base_queryset = LICENSE_LINE_QS


SUPPORT_TAB = dict(label='Support', badge=_lines_badge(CoverageLine),
                   permission='netbox_tco.view_coverageline', weight=2100)
LICENSES_TAB = dict(label='Licenses', badge=_lines_badge(LicenseLine),
                    permission='netbox_tco.view_licenseline', weight=2110)


@register_model_view(Device, 'tco_support', path='support')
class DeviceSupportView(_SupportTabView):
    queryset = Device.objects.all()
    tab = ViewTab(**SUPPORT_TAB)


@register_model_view(Module, 'tco_support', path='support')
class ModuleSupportView(_SupportTabView):
    queryset = Module.objects.all()
    tab = ViewTab(**SUPPORT_TAB)


@register_model_view(Device, 'tco_licenses', path='licenses')
class DeviceLicensesView(_LicensesTabView):
    queryset = Device.objects.all()
    tab = ViewTab(**LICENSES_TAB)


@register_model_view(Module, 'tco_licenses', path='licenses')
class ModuleLicensesView(_LicensesTabView):
    queryset = Module.objects.all()
    tab = ViewTab(**LICENSES_TAB)


# ---------------------------------------------------------------------------
# Lifecycle Records
# ---------------------------------------------------------------------------

@register_model_view(LifecycleRecord, 'list', path='', detail=False)
class LifecycleRecordListView(ObjectListView):
    queryset = LifecycleRecord.objects.prefetch_related('milestones__milestone_type').annotate(
        device_type_count=Count('device_types', distinct=True),
        module_type_count=Count('module_types', distinct=True),
    )
    table = LifecycleRecordTable
    filterset = LifecycleRecordFilterSet
    filterset_form = LifecycleRecordFilterForm


@register_model_view(LifecycleRecord)
class LifecycleRecordView(ObjectView):
    queryset = LifecycleRecord.objects.prefetch_related('device_types', 'module_types', 'milestones__milestone_type')

    def get_extra_context(self, request, instance):
        from .template_content import milestone_rows
        ct = ContentType.objects.get_for_model(LifecycleRecord)
        return {
            'milestones': milestone_rows(instance),
            'device_types': instance.device_types.select_related('manufacturer').annotate(
                tco_instance_count=Count('instances', distinct=True),
            ),
            'module_types': instance.module_types.select_related('manufacturer').annotate(
                tco_instance_count=Count('instances', distinct=True),
            ),
            'attachments': Attachment.objects.filter(
                content_type=ct, object_id=instance.pk
            ).select_related('uploaded_by'),
        }


@register_model_view(LifecycleRecord, 'add', detail=False)
@register_model_view(LifecycleRecord, 'edit')
class LifecycleRecordEditView(ObjectEditView):
    queryset = LifecycleRecord.objects.all()
    form = LifecycleRecordForm


@register_model_view(LifecycleRecord, 'delete')
class LifecycleRecordDeleteView(ObjectDeleteView):
    queryset = LifecycleRecord.objects.all()


# ---------------------------------------------------------------------------
# Milestone Types
# ---------------------------------------------------------------------------

@register_model_view(MilestoneType, 'list', path='', detail=False)
class MilestoneTypeListView(ObjectListView):
    queryset = MilestoneType.objects.annotate(milestone_count=Count('milestones'))
    table = MilestoneTypeTable
    filterset = MilestoneTypeFilterSet
    filterset_form = MilestoneTypeFilterForm


@register_model_view(MilestoneType)
class MilestoneTypeView(ObjectView):
    queryset = MilestoneType.objects.all()

    def get_extra_context(self, request, instance):
        return {'milestones': instance.milestones.select_related('lifecycle_record').order_by('date')}


@register_model_view(MilestoneType, 'add', detail=False)
@register_model_view(MilestoneType, 'edit')
class MilestoneTypeEditView(ObjectEditView):
    queryset = MilestoneType.objects.all()
    form = MilestoneTypeForm


@register_model_view(MilestoneType, 'delete')
class MilestoneTypeDeleteView(ObjectDeleteView):
    queryset = MilestoneType.objects.all()


# ---------------------------------------------------------------------------
# Lifecycle Milestones
# ---------------------------------------------------------------------------

class LifecycleMilestoneCreateView(PermissionRequiredMixin, View):
    permission_required = 'netbox_tco.add_lifecyclemilestone'

    def _render(self, request, record, form):
        return render(request, 'netbox_tco/partnumber_edit.html', {
            'object': record,
            'form': form,
            'title': f'Add Milestone — {record}',
            'cancel_url': record.get_absolute_url(),
        })

    def get(self, request, record_pk):
        record = get_object_or_404(LifecycleRecord, pk=record_pk)
        return self._render(request, record, LifecycleMilestoneForm(lifecycle_record=record))

    def post(self, request, record_pk):
        record = get_object_or_404(LifecycleRecord, pk=record_pk)
        form = LifecycleMilestoneForm(request.POST, lifecycle_record=record)
        if form.is_valid():
            milestone = form.save(commit=False)
            milestone.lifecycle_record = record
            milestone.save()
            messages.success(request, f'Added {milestone.milestone_type} date.')
            return redirect(record.get_absolute_url())
        return self._render(request, record, form)


class LifecycleMilestoneEditView(PermissionRequiredMixin, View):
    permission_required = 'netbox_tco.change_lifecyclemilestone'

    def _render(self, request, milestone, form):
        return render(request, 'netbox_tco/partnumber_edit.html', {
            'object': milestone.lifecycle_record,
            'form': form,
            'title': f'Edit Milestone — {milestone.milestone_type}',
            'cancel_url': milestone.lifecycle_record.get_absolute_url(),
        })

    def get(self, request, pk):
        milestone = get_object_or_404(LifecycleMilestone, pk=pk)
        form = LifecycleMilestoneForm(instance=milestone, lifecycle_record=milestone.lifecycle_record)
        return self._render(request, milestone, form)

    def post(self, request, pk):
        milestone = get_object_or_404(LifecycleMilestone, pk=pk)
        form = LifecycleMilestoneForm(request.POST, instance=milestone, lifecycle_record=milestone.lifecycle_record)
        if form.is_valid():
            form.save()
            messages.success(request, f'Updated {milestone.milestone_type} date.')
            return redirect(milestone.lifecycle_record.get_absolute_url())
        return self._render(request, milestone, form)


class LifecycleMilestoneDeleteView(PermissionRequiredMixin, View):
    permission_required = 'netbox_tco.delete_lifecyclemilestone'

    def get(self, request, pk):
        milestone = get_object_or_404(LifecycleMilestone, pk=pk)
        return render(request, 'netbox_tco/partnumber_confirm_delete.html', {
            'object': milestone.lifecycle_record,
            'target': milestone,
            'noun': 'milestone',
            'cancel_url': milestone.lifecycle_record.get_absolute_url(),
        })

    def post(self, request, pk):
        milestone = get_object_or_404(LifecycleMilestone, pk=pk)
        record = milestone.lifecycle_record
        milestone.delete()
        messages.success(request, f'Deleted {milestone.milestone_type} date.')
        return redirect(record.get_absolute_url())
