import django_filters
from django.db.models import Q
from dcim.models import DeviceType, Manufacturer
from netbox.filtersets import NetBoxModelFilterSet
from utilities.filtersets import register_filterset

from .choices import (
    BillingTermChoices, ContractStatusChoices, CoverageStatusChoices, LineItemTypeChoices, QPIStatusChoices,
    RenewalStatusChoices,
)
from .models import (
    CoverageLine, License, LicenseLine, LicenseType, LifecycleRecord, LineItem, QPI, ServiceLevel,
    SupportContract,
)


@register_filterset
class ServiceLevelFilterSet(NetBoxModelFilterSet):
    manufacturer_id = django_filters.ModelMultipleChoiceFilter(
        field_name='part_numbers__manufacturer',
        queryset=Manufacturer.objects.all(),
        label='Manufacturer',
    )
    part_number = django_filters.CharFilter(
        field_name='part_numbers__part_number',
        lookup_expr='icontains',
        label='Part number',
    )

    class Meta:
        model = ServiceLevel
        fields = ['name', 'slug']

    def search(self, queryset, name, value):
        return queryset.filter(
            Q(name__icontains=value) | Q(part_numbers__part_number__icontains=value)
        ).distinct()


@register_filterset
class LicenseTypeFilterSet(NetBoxModelFilterSet):
    manufacturer_id = django_filters.ModelMultipleChoiceFilter(
        field_name='part_numbers__manufacturer',
        queryset=Manufacturer.objects.all(),
        label='Manufacturer',
    )
    part_number = django_filters.CharFilter(
        field_name='part_numbers__part_number',
        lookup_expr='icontains',
        label='Part number',
    )

    class Meta:
        model = LicenseType
        fields = ['name', 'slug']

    def search(self, queryset, name, value):
        return queryset.filter(
            Q(name__icontains=value) | Q(part_numbers__part_number__icontains=value)
        ).distinct()


@register_filterset
class QPIFilterSet(NetBoxModelFilterSet):
    status = django_filters.MultipleChoiceFilter(choices=QPIStatusChoices)

    class Meta:
        model = QPI
        fields = ['name', 'status']

    def search(self, queryset, name, value):
        return queryset.filter(name__icontains=value)


@register_filterset
class LineItemFilterSet(NetBoxModelFilterSet):
    qpi_id = django_filters.ModelMultipleChoiceFilter(
        queryset=QPI.objects.all(),
        label='QPI',
    )
    line_type = django_filters.MultipleChoiceFilter(choices=LineItemTypeChoices)

    class Meta:
        model = LineItem
        fields = ['qpi_id', 'line_type']

    def search(self, queryset, name, value):
        return queryset.filter(
            Q(name__icontains=value) |
            Q(qpi__name__icontains=value) |
            Q(description__icontains=value)
        ).distinct()


@register_filterset
class SupportContractFilterSet(NetBoxModelFilterSet):
    status = django_filters.MultipleChoiceFilter(choices=ContractStatusChoices)
    renewal_status = django_filters.MultipleChoiceFilter(choices=RenewalStatusChoices)
    vendor_id = django_filters.ModelMultipleChoiceFilter(
        field_name='vendor',
        queryset=Manufacturer.objects.all(),
        label='Vendor',
    )

    class Meta:
        model = SupportContract
        fields = ['name', 'status', 'renewal_status', 'contract_id']

    def search(self, queryset, name, value):
        return queryset.filter(
            Q(name__icontains=value) | Q(contract_id__icontains=value) | Q(description__icontains=value)
        )


class AssignedObjectFilterMixin(django_filters.FilterSet):
    device_id = django_filters.NumberFilter(method='filter_assigned', label='Device (ID)')
    module_id = django_filters.NumberFilter(method='filter_assigned', label='Module (ID)')

    def filter_assigned(self, queryset, name, value):
        model_name = name.removesuffix('_id')
        return queryset.filter(
            assigned_object_type__app_label='dcim',
            assigned_object_type__model=model_name,
            assigned_object_id=value,
        )


@register_filterset
class CoverageLineFilterSet(AssignedObjectFilterMixin, NetBoxModelFilterSet):
    support_contract_id = django_filters.ModelMultipleChoiceFilter(
        field_name='support_contract',
        queryset=SupportContract.objects.all(),
        label='Support contract',
    )
    funding_line_item_id = django_filters.ModelMultipleChoiceFilter(
        field_name='funding_line_item',
        queryset=LineItem.objects.all(),
        label='Funding line item',
    )
    service_level_id = django_filters.ModelMultipleChoiceFilter(
        field_name='service_level',
        queryset=ServiceLevel.objects.all(),
        label='Service level',
    )
    status = django_filters.MultipleChoiceFilter(choices=CoverageStatusChoices)

    class Meta:
        model = CoverageLine
        fields = ['status', 'start_date', 'end_date', 'price']

    def search(self, queryset, name, value):
        return queryset.filter(
            Q(support_contract__name__icontains=value) |
            Q(support_contract__contract_id__icontains=value)
        )


@register_filterset
class LicenseFilterSet(NetBoxModelFilterSet):
    status = django_filters.MultipleChoiceFilter(choices=ContractStatusChoices)
    renewal_status = django_filters.MultipleChoiceFilter(choices=RenewalStatusChoices)
    vendor_id = django_filters.ModelMultipleChoiceFilter(
        field_name='vendor',
        queryset=Manufacturer.objects.all(),
        label='Vendor',
    )

    class Meta:
        model = License
        fields = ['name', 'status', 'renewal_status', 'license_number']

    def search(self, queryset, name, value):
        return queryset.filter(
            Q(name__icontains=value) | Q(license_number__icontains=value) | Q(description__icontains=value)
        )


@register_filterset
class LicenseLineFilterSet(AssignedObjectFilterMixin, NetBoxModelFilterSet):
    license_id = django_filters.ModelMultipleChoiceFilter(
        field_name='license',
        queryset=License.objects.all(),
        label='License',
    )
    funding_line_item_id = django_filters.ModelMultipleChoiceFilter(
        field_name='funding_line_item',
        queryset=LineItem.objects.all(),
        label='Funding line item',
    )
    license_type_id = django_filters.ModelMultipleChoiceFilter(
        field_name='license_type',
        queryset=LicenseType.objects.all(),
        label='License type',
    )
    status = django_filters.MultipleChoiceFilter(choices=CoverageStatusChoices)
    billing_term = django_filters.MultipleChoiceFilter(choices=BillingTermChoices)

    class Meta:
        model = LicenseLine
        fields = ['status', 'billing_term', 'start_date', 'end_date', 'price']

    def search(self, queryset, name, value):
        return queryset.filter(
            Q(license__name__icontains=value) |
            Q(license__license_number__icontains=value)
        )


@register_filterset
class LifecycleRecordFilterSet(NetBoxModelFilterSet):
    device_type_id = django_filters.ModelMultipleChoiceFilter(
        field_name='device_types',
        queryset=DeviceType.objects.all(),
        label='Device type',
    )

    class Meta:
        model = LifecycleRecord
        fields = ['name']

    def search(self, queryset, name, value):
        return queryset.filter(name__icontains=value)
