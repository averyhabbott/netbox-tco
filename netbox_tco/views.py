from datetime import date
from decimal import Decimal

from dcim.models import Device, Module
from django.apps import apps
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Count, Max
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from netbox.object_actions import AddObject, BulkDelete, BulkEdit, BulkExport, DeleteObject, EditObject
from netbox.views.generic import (
    BulkDeleteView, BulkEditView, ObjectChildrenView, ObjectDeleteView, ObjectEditView,
    ObjectListView, ObjectView,
)
from utilities.views import ViewTab, register_model_view

from .choices import ContractStatusChoices, CoverageStatusChoices, LineItemTypeChoices
from .provisioning import coverable_limit_choices_to, coverable_model_names

from .filtersets import (
    CoverageLineFilterSet, LicenseFilterSet, LicenseTypeFilterSet, LifecycleRecordFilterSet,
    LineItemFilterSet, QPIFilterSet, ServiceLevelFilterSet, SupportContractFilterSet,
)
from .forms import (
    AddToSupportContractForm, AssignCoverageForm, AttachmentForm, CoverageLineBulkEditForm,
    CoverageLineFilterForm, CoverageLineForm, LicenseFilterForm, LicenseForm, LicenseLineForm,
    LicensePartNumberForm, LicenseTypeForm, LicenseTypeFilterForm,
    LifecycleRecordForm, LifecycleRecordFilterForm, LifecycleMilestoneForm,
    LineItemForm, LineItemFilterForm, QPIForm, QPIFilterForm,
    ServiceLevelForm, ServiceLevelFilterForm, ServiceLevelPartNumberForm,
    SupportContractForm, SupportContractFilterForm,
)
from .models import (
    Attachment, CoverageLine, License, LicenseLine, LicensePartNumber, LicenseType,
    LifecycleMilestone, LifecycleRecord, LineItem, ProvisionedItem, QPI, ServiceLevel,
    ServiceLevelPartNumber, SupportContract,
)
from .tables import (
    CoverageLineTable, LicenseTable, LicenseTypeTable, LifecycleRecordTable,
    LineItemTable, QPITable, ServiceLevelTable, SupportContractTable,
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
            'object': pn,
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
            'object': pn,
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
    permission_required = 'netbox_tco.add_attachment'

    def get(self, request, qpi_pk):
        qpi = get_object_or_404(QPI, pk=qpi_pk)
        form = AttachmentForm()
        return render(request, 'netbox_tco/attachment_edit.html', {
            'object': qpi,
            'form': form,
            'title': f'Add Attachment — {qpi}',
            'cancel_url': qpi.get_absolute_url(),
        })

    def post(self, request, qpi_pk):
        from django.contrib.contenttypes.models import ContentType
        qpi = get_object_or_404(QPI, pk=qpi_pk)
        form = AttachmentForm(request.POST, request.FILES)
        if form.is_valid():
            att = form.save(commit=False)
            att.content_type = ContentType.objects.get_for_model(QPI)
            att.object_id = qpi.pk
            att.uploaded_by = request.user
            att.save()
            messages.success(request, f'Added attachment {att.name}.')
            return redirect(qpi.get_absolute_url())
        return render(request, 'netbox_tco/attachment_edit.html', {
            'object': qpi,
            'form': form,
            'title': f'Add Attachment — {qpi}',
            'cancel_url': qpi.get_absolute_url(),
        })


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
            'object': att,
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

        coverage_lines = []
        coverage_remaining = 0
        if instance.line_type == LineItemTypeChoices.TYPE_SUPPORT:
            coverage_lines = list(
                instance.coverage_lines.select_related('support_contract', 'assigned_object_type')
                .prefetch_related('assigned_object')
                .order_by('support_contract__name', 'pk')
            )
            coverage_remaining = max(0, instance.quantity - len(coverage_lines))

        return {
            'provisioned_items': provisioned_items,
            'remaining': remaining,
            'provision_url': provision_url,
            'coverage_lines': coverage_lines,
            'coverage_remaining': coverage_remaining,
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

    def get_extra_context(self, request, instance):
        lines = list(
            instance.coverage_lines.select_related(
                'service_level', 'funding_line_item__qpi', 'assigned_object_type',
            ).prefetch_related('assigned_object')
        )
        lines.sort(key=lambda l: (-l.end_date.toordinal(), str(l.assigned_object or ''), l.pk))
        status_counts = {}
        for line in lines:
            status_counts[line.get_status_display()] = status_counts.get(line.get_status_display(), 0) + 1
        start = min((l.start_date for l in lines), default=None)
        end = max((l.end_date for l in lines), default=None)
        return {
            'coverage_lines': lines,
            'status_counts': status_counts,
            'contract_start': start,
            'contract_end': end,
            'is_expired': end is not None and end < date.today(),
            'contract_total': sum((l.price for l in lines), Decimal('0')),
            'funding_line_items': instance.funding_line_items.select_related('qpi'),
        }


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


def _overlapping_keys(contract, start, end):
    """Objects already assigned on `contract` with a line overlapping (start, end); touching ends don't count."""
    return set(
        contract.coverage_lines.filter(
            status=CoverageStatusChoices.STATUS_ASSIGNED,
            start_date__lt=end,
            end_date__gt=start,
        ).values_list('assigned_object_type_id', 'assigned_object_id')
    )


class AddToSupportContractView(PermissionRequiredMixin, View):
    """Create coverage lines on a new or existing contract, funded by a support line item."""
    permission_required = ('netbox_tco.add_coverageline', 'netbox_tco.add_supportcontract')
    template_name = 'netbox_tco/lineitem_add_to_contract.html'

    def _get_line_item(self, pk):
        return get_object_or_404(
            LineItem.objects.select_related('qpi', 'support_sku__manufacturer', 'support_sku__service_level'),
            pk=pk, line_type=LineItemTypeChoices.TYPE_SUPPORT,
        )

    def _render(self, request, line_item, form, remaining):
        return render(request, self.template_name, {
            'object': line_item,
            'form': form,
            'remaining': remaining,
            'return_url': line_item.get_absolute_url(),
        })

    def get(self, request, pk):
        line_item = self._get_line_item(pk)
        remaining = line_item.quantity - line_item.coverage_lines.count()
        if remaining <= 0:
            messages.warning(request, 'Every unit on this line item already funds a coverage line.')
            return redirect(line_item.get_absolute_url())
        initial = {
            'mode': AddToSupportContractForm.MODE_NEW,
            'name': line_item.name or str(line_item.support_sku),
            'vendor': line_item.support_sku.manufacturer,
            'seed': AddToSupportContractForm.SEED_PENDING,
            'start_date': line_item.start_date,
            'end_date': line_item.end_date,
            'price': line_item.unit_price,
        }
        contract_pk = request.GET.get('contract')
        if contract_pk and contract_pk.isdigit():
            initial['mode'] = AddToSupportContractForm.MODE_EXISTING
            initial['existing_contract'] = contract_pk
        form = AddToSupportContractForm(initial=initial)
        return self._render(request, line_item, form, remaining)

    def post(self, request, pk):
        line_item = self._get_line_item(pk)
        remaining = line_item.quantity - line_item.coverage_lines.count()
        form = AddToSupportContractForm(request.POST)
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
                    line_item__qpi=line_item.qpi,
                    content_type_id__in=coverable_ct_ids,
                ).order_by('content_type_id', 'object_id').values_list('content_type_id', 'object_id')
            )
        elif cd['seed'] == form.SEED_CONTRACT:
            source = form.get_source_contract()
            candidates = list(
                source.coverage_lines.filter(status=CoverageStatusChoices.STATUS_ASSIGNED)
                .order_by('assigned_object_type_id', 'assigned_object_id')
                .values_list('assigned_object_type_id', 'assigned_object_id').distinct()
            )

        if target is not None:
            already = _overlapping_keys(target, start, end)
            candidates = [c for c in candidates if c not in already]

        if len(candidates) > remaining:
            form.add_error(
                'seed',
                f'Found {len(candidates)} devices/modules to cover, but this line item only has '
                f'{remaining} unit(s) left. Increase its quantity or pick "Blank pending lines".'
            )
            return self._render(request, line_item, form, remaining)

        with transaction.atomic():
            if target is None:
                target = SupportContract(
                    name=cd['name'],
                    contract_id=cd['contract_id'],
                    vendor=cd['vendor'],
                    status=(ContractStatusChoices.STATUS_PENDING if start > date.today()
                            else ContractStatusChoices.STATUS_ACTIVE),
                )
                target.full_clean()
                target.save()
                target.predecessors.set(cd['predecessors'])

            common = dict(
                support_contract=target,
                funding_line_item=line_item,
                service_level=line_item.support_sku.service_level,
                start_date=start,
                end_date=end,
                price=price,
            )
            for ct_id, obj_id in candidates:
                CoverageLine(assigned_object_type_id=ct_id, assigned_object_id=obj_id, **common).save()
            pending = remaining - len(candidates)
            for _ in range(pending):
                CoverageLine(**common).save()
            target.apply_status_transitions()

        messages.success(
            request,
            f'Added {len(candidates)} assigned and {pending} pending coverage line(s) to {target}.'
        )
        return redirect(target.get_absolute_url())


class AssignCoverageView(PermissionRequiredMixin, View):
    """Fill a contract's pending coverage lines with devices/modules selected on a core list page."""
    permission_required = 'netbox_tco.change_coverageline'
    template_name = 'netbox_tco/coverage_assign.html'

    def _setup(self, request, model_name):
        if model_name not in coverable_model_names():
            raise Http404
        model = apps.get_model('dcim', model_name)
        pk_list = [int(pk) for pk in request.POST.getlist('pk') if pk.isdigit()]
        objects = list(model.objects.filter(pk__in=pk_list).order_by('pk'))
        return_url = request.POST.get('return_url') or reverse(f'dcim:{model_name}_list')
        if not url_has_allowed_host_and_scheme(return_url, allowed_hosts=None):
            return_url = reverse(f'dcim:{model_name}_list')
        return model, objects, return_url

    def post(self, request, model_name):
        model, objects, return_url = self._setup(request, model_name)
        if not objects:
            messages.warning(request, f'No {model._meta.verbose_name_plural} selected.')
            return redirect(return_url)

        form = AssignCoverageForm(request.POST if '_confirm' in request.POST else None)
        if '_confirm' not in request.POST or not form.is_valid():
            return render(request, self.template_name, {
                'form': form,
                'objects': objects,
                'model_name': model_name,
                'verbose_name_plural': model._meta.verbose_name_plural,
                'return_url': return_url,
            })

        contract = form.cleaned_data['support_contract']
        ct = ContentType.objects.get_for_model(model)
        assigned, skipped = 0, []
        with transaction.atomic():
            pending = list(
                contract.coverage_lines.select_for_update()
                .filter(status=CoverageStatusChoices.STATUS_PENDING)
                .order_by('start_date', 'pk')
            )
            for obj in objects:
                if not pending:
                    skipped.append(obj)
                    continue
                line = pending[0]
                if (ct.pk, obj.pk) in _overlapping_keys(contract, line.start_date, line.end_date):
                    skipped.append(obj)
                    continue
                pending.pop(0)
                line.snapshot()
                line.assigned_object = obj
                line.save()
                assigned += 1

        if assigned:
            messages.success(request, f'Assigned {assigned} {model._meta.verbose_name_plural} to {contract}.')
        if skipped:
            messages.warning(
                request,
                f'Skipped {len(skipped)} (already covered for that term, or no pending lines left): '
                + ', '.join(str(o) for o in skipped[:10]) + ('…' if len(skipped) > 10 else '')
            )
        return redirect(contract.get_absolute_url())


class _SupportTabView(ObjectChildrenView):
    child_model = CoverageLine
    table = CoverageLineTable
    filterset = CoverageLineFilterSet
    actions = (EditObject, DeleteObject, BulkEdit, BulkDelete)

    def get_children(self, request, parent):
        ct = ContentType.objects.get_for_model(parent)
        return COVERAGE_LINE_QS.filter(assigned_object_type=ct, assigned_object_id=parent.pk)


def _support_badge(obj):
    ct = ContentType.objects.get_for_model(obj)
    return CoverageLine.objects.filter(assigned_object_type=ct, assigned_object_id=obj.pk).count()


@register_model_view(Device, 'tco_support', path='support')
class DeviceSupportView(_SupportTabView):
    queryset = Device.objects.all()
    tab = ViewTab(label='Support', badge=_support_badge, permission='netbox_tco.view_coverageline', weight=2100)


@register_model_view(Module, 'tco_support', path='support')
class ModuleSupportView(_SupportTabView):
    queryset = Module.objects.all()
    tab = ViewTab(label='Support', badge=_support_badge, permission='netbox_tco.view_coverageline', weight=2100)


# ---------------------------------------------------------------------------
# Licenses
# ---------------------------------------------------------------------------

@register_model_view(License, 'list', path='', detail=False)
class LicenseListView(ObjectListView):
    queryset = License.objects.select_related('vendor')
    table = LicenseTable
    filterset = LicenseFilterSet
    filterset_form = LicenseFilterForm


@register_model_view(License)
class LicenseView(ObjectView):
    queryset = License.objects.select_related('vendor').prefetch_related(
        'license_lines__device', 'license_lines__license_type',
        'predecessors', 'funding_line_items',
    )

    def get_extra_context(self, request, instance):
        return {
            'license_lines': instance.license_lines.select_related('device', 'license_type'),
        }


@register_model_view(License, 'add', detail=False)
@register_model_view(License, 'edit')
class LicenseEditView(ObjectEditView):
    queryset = License.objects.all()
    form = LicenseForm


@register_model_view(License, 'delete')
class LicenseDeleteView(ObjectDeleteView):
    queryset = License.objects.all()


# ---------------------------------------------------------------------------
# Lifecycle Records
# ---------------------------------------------------------------------------

@register_model_view(LifecycleRecord, 'list', path='', detail=False)
class LifecycleRecordListView(ObjectListView):
    queryset = LifecycleRecord.objects.annotate(
        device_type_count=Count('device_types')
    )
    table = LifecycleRecordTable
    filterset = LifecycleRecordFilterSet
    filterset_form = LifecycleRecordFilterForm


@register_model_view(LifecycleRecord)
class LifecycleRecordView(ObjectView):
    queryset = LifecycleRecord.objects.prefetch_related('device_types', 'milestones')

    def get_extra_context(self, request, instance):
        return {
            'milestones': instance.milestones.order_by('date'),
            'device_types': instance.device_types.select_related('manufacturer'),
        }


@register_model_view(LifecycleRecord, 'add', detail=False)
@register_model_view(LifecycleRecord, 'edit')
class LifecycleRecordEditView(ObjectEditView):
    queryset = LifecycleRecord.objects.all()
    form = LifecycleRecordForm


@register_model_view(LifecycleRecord, 'delete')
class LifecycleRecordDeleteView(ObjectDeleteView):
    queryset = LifecycleRecord.objects.all()
