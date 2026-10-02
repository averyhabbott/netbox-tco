from django.contrib.contenttypes.models import ContentType
from netbox.api.fields import ChoiceField, ContentTypeField
from netbox.api.gfk_fields import GFKSerializerField
from netbox.api.serializers import NetBoxModelSerializer
from rest_framework import serializers

from ..choices import BillingTermChoices, ContractStatusChoices, CoverageStatusChoices, RenewalStatusChoices
from ..provisioning import coverable_limit_choices_to

from ..models import (
    CoverageLine, License, LicenseLine, LicensePartNumber, LicenseType,
    LifecycleMilestone, LifecycleRecord, LineItem, QPI, ServiceLevel,
    ServiceLevelPartNumber, SupportContract,
)


class ServiceLevelSerializer(NetBoxModelSerializer):
    class Meta:
        model = ServiceLevel
        fields = ('id', 'url', 'display', 'name', 'slug', 'description',
                  'tags', 'custom_fields', 'created', 'last_updated')
        brief_fields = ('id', 'url', 'display', 'name', 'slug')


class ServiceLevelPartNumberSerializer(serializers.ModelSerializer):
    display = serializers.SerializerMethodField()

    def get_display(self, obj):
        return str(obj)

    class Meta:
        model = ServiceLevelPartNumber
        fields = ('id', 'display', 'service_level', 'part_number', 'manufacturer', 'description')


class LicenseTypeSerializer(NetBoxModelSerializer):
    class Meta:
        model = LicenseType
        fields = ('id', 'url', 'display', 'name', 'slug', 'description',
                  'tags', 'custom_fields', 'created', 'last_updated')
        brief_fields = ('id', 'url', 'display', 'name', 'slug')


class LicensePartNumberSerializer(serializers.ModelSerializer):
    display = serializers.SerializerMethodField()

    def get_display(self, obj):
        return str(obj)

    class Meta:
        model = LicensePartNumber
        fields = ('id', 'display', 'license_type', 'part_number', 'manufacturer', 'description')


class QPISerializer(NetBoxModelSerializer):
    class Meta:
        model = QPI
        fields = ('id', 'url', 'display', 'name', 'description', 'status', 'owners',
                  'quote_requested', 'quote_received', 'quote_signed',
                  'auto_populate_returned', 'quote_returned',
                  'ship_date', 'received_date',
                  'tags', 'custom_fields', 'created', 'last_updated')
        brief_fields = ('id', 'url', 'display', 'name', 'status')


class LineItemSerializer(NetBoxModelSerializer):
    line_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    end_date = serializers.DateField(read_only=True)

    class Meta:
        model = LineItem
        fields = ('id', 'url', 'display', 'qpi', 'line_type', 'name',
                  'device_type', 'module_type', 'rack_type',
                  'support_sku', 'license_sku', 'quantity', 'unit_price', 'line_total',
                  'term_months', 'start_date', 'end_date', 'description',
                  'tags', 'custom_fields', 'created', 'last_updated')
        brief_fields = ('id', 'url', 'display', 'qpi', 'line_type', 'name', 'quantity', 'unit_price')


class SupportContractSerializer(NetBoxModelSerializer):
    status = ChoiceField(choices=ContractStatusChoices, required=False)
    renewal_status = ChoiceField(choices=RenewalStatusChoices, read_only=True)
    start_date = serializers.DateField(read_only=True)
    end_date = serializers.DateField(read_only=True)
    total_price = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = SupportContract
        fields = ('id', 'url', 'display', 'name', 'vendor', 'contract_id', 'status',
                  'renewal_status', 'renewal_date', 'start_date', 'end_date', 'total_price',
                  'predecessors', 'description', 'tags', 'custom_fields', 'created', 'last_updated')
        brief_fields = ('id', 'url', 'display', 'name', 'contract_id', 'status')


class CoverageLineSerializer(NetBoxModelSerializer):
    status = ChoiceField(choices=CoverageStatusChoices, read_only=True)
    assigned_object_type = ContentTypeField(
        queryset=ContentType.objects.filter(coverable_limit_choices_to()),
        required=False,
        allow_null=True,
    )
    assigned_object = GFKSerializerField(read_only=True)

    class Meta:
        model = CoverageLine
        fields = ('id', 'url', 'display', 'support_contract', 'assigned_object_type',
                  'assigned_object_id', 'assigned_object', 'status', 'funding_line_item',
                  'service_level', 'start_date', 'end_date', 'price',
                  'tags', 'custom_fields', 'created', 'last_updated')
        brief_fields = ('id', 'url', 'display', 'support_contract', 'status')


class LicenseSerializer(NetBoxModelSerializer):
    status = ChoiceField(choices=ContractStatusChoices, required=False)
    renewal_status = ChoiceField(choices=RenewalStatusChoices, read_only=True)
    start_date = serializers.DateField(read_only=True)
    end_date = serializers.DateField(read_only=True)
    total_price = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = License
        fields = ('id', 'url', 'display', 'name', 'vendor', 'license_number', 'status',
                  'renewal_status', 'renewal_date', 'start_date', 'end_date', 'total_price',
                  'predecessors', 'description', 'tags', 'custom_fields', 'created', 'last_updated')
        brief_fields = ('id', 'url', 'display', 'name', 'license_number', 'status')


class LicenseLineSerializer(NetBoxModelSerializer):
    status = ChoiceField(choices=CoverageStatusChoices, read_only=True)
    billing_term = ChoiceField(choices=BillingTermChoices, required=False, allow_blank=True)
    assigned_object_type = ContentTypeField(
        queryset=ContentType.objects.filter(coverable_limit_choices_to()),
        required=False,
        allow_null=True,
    )
    assigned_object = GFKSerializerField(read_only=True)

    class Meta:
        model = LicenseLine
        fields = ('id', 'url', 'display', 'license', 'assigned_object_type',
                  'assigned_object_id', 'assigned_object', 'status', 'funding_line_item',
                  'license_type', 'billing_term', 'start_date', 'end_date', 'price', 'license_key',
                  'tags', 'custom_fields', 'created', 'last_updated')
        brief_fields = ('id', 'url', 'display', 'license', 'status')


class LifecycleRecordSerializer(NetBoxModelSerializer):
    class Meta:
        model = LifecycleRecord
        fields = ('id', 'url', 'display', 'name', 'device_types', 'reference_url',
                  'notice_date', 'tags', 'custom_fields', 'created', 'last_updated')
        brief_fields = ('id', 'url', 'display', 'name')


class LifecycleMilestoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = LifecycleMilestone
        fields = ('id', 'lifecycle_record', 'milestone_type', 'date')
