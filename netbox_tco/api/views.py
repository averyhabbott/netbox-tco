from netbox.api.viewsets import NetBoxModelViewSet
from rest_framework.viewsets import ReadOnlyModelViewSet

from ..filtersets import (
    CoverageLineFilterSet, LicenseFilterSet, LicenseLineFilterSet, LicenseTypeFilterSet, LifecycleRecordFilterSet,
    LineItemFilterSet, MilestoneTypeFilterSet, QPIFilterSet, ServiceLevelFilterSet, SupportContractFilterSet,
)
from ..models import (
    CoverageLine, License, LicenseLine, LicensePartNumber, LicenseType, LifecycleMilestone, LifecycleRecord, LineItem, MilestoneType, QPI,
    ServiceLevel, ServiceLevelPartNumber, SupportContract,
)
from .serializers import (
    CoverageLineSerializer, LicenseLineSerializer, LicensePartNumberSerializer, LicenseSerializer, LicenseTypeSerializer,
    LifecycleMilestoneSerializer, LifecycleRecordSerializer, LineItemSerializer, MilestoneTypeSerializer, QPISerializer,
    ServiceLevelPartNumberSerializer, ServiceLevelSerializer, SupportContractSerializer,
)


class ServiceLevelViewSet(NetBoxModelViewSet):
    queryset = ServiceLevel.objects.prefetch_related('part_numbers', 'tags')
    serializer_class = ServiceLevelSerializer
    filterset_class = ServiceLevelFilterSet


class ServiceLevelPartNumberViewSet(ReadOnlyModelViewSet):
    queryset = ServiceLevelPartNumber.objects.select_related('manufacturer', 'service_level')
    serializer_class = ServiceLevelPartNumberSerializer


class LicenseTypeViewSet(NetBoxModelViewSet):
    queryset = LicenseType.objects.prefetch_related('part_numbers', 'tags')
    serializer_class = LicenseTypeSerializer
    filterset_class = LicenseTypeFilterSet


class LicensePartNumberViewSet(ReadOnlyModelViewSet):
    queryset = LicensePartNumber.objects.select_related('manufacturer', 'license_type')
    serializer_class = LicensePartNumberSerializer


class QPIViewSet(NetBoxModelViewSet):
    queryset = QPI.objects.prefetch_related('owners', 'tags')
    serializer_class = QPISerializer
    filterset_class = QPIFilterSet


class LineItemViewSet(NetBoxModelViewSet):
    queryset = LineItem.objects.select_related(
        'qpi', 'device_type', 'module_type', 'rack_type', 'support_sku', 'license_sku'
    ).prefetch_related('tags')
    serializer_class = LineItemSerializer
    filterset_class = LineItemFilterSet


class SupportContractViewSet(NetBoxModelViewSet):
    queryset = SupportContract.objects.select_related('vendor').prefetch_related(
        'predecessors', 'tags'
    )
    serializer_class = SupportContractSerializer
    filterset_class = SupportContractFilterSet


class CoverageLineViewSet(NetBoxModelViewSet):
    queryset = CoverageLine.objects.select_related(
        'support_contract', 'funding_line_item', 'service_level', 'assigned_object_type',
    ).prefetch_related('tags')
    serializer_class = CoverageLineSerializer
    filterset_class = CoverageLineFilterSet


class LicenseViewSet(NetBoxModelViewSet):
    queryset = License.objects.select_related('vendor').prefetch_related(
        'predecessors', 'tags'
    )
    serializer_class = LicenseSerializer
    filterset_class = LicenseFilterSet


class LicenseLineViewSet(NetBoxModelViewSet):
    queryset = LicenseLine.objects.select_related(
        'license', 'funding_line_item', 'license_type', 'assigned_object_type',
    ).prefetch_related('tags')
    serializer_class = LicenseLineSerializer
    filterset_class = LicenseLineFilterSet


class MilestoneTypeViewSet(NetBoxModelViewSet):
    queryset = MilestoneType.objects.prefetch_related('tags')
    serializer_class = MilestoneTypeSerializer
    filterset_class = MilestoneTypeFilterSet


class LifecycleRecordViewSet(NetBoxModelViewSet):
    queryset = LifecycleRecord.objects.prefetch_related(
        'device_types', 'module_types', 'rack_types', 'milestones', 'tags',
    )
    serializer_class = LifecycleRecordSerializer
    filterset_class = LifecycleRecordFilterSet


class LifecycleMilestoneViewSet(ReadOnlyModelViewSet):
    queryset = LifecycleMilestone.objects.select_related('lifecycle_record', 'milestone_type')
    serializer_class = LifecycleMilestoneSerializer
