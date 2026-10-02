import django_tables2 as tables
from netbox.tables import NetBoxTable, columns

from .models import (
    CoverageLine, License, LicenseLine, LicensePartNumber, LicenseType,
    LifecycleMilestone, LifecycleRecord, LineItem, QPI, ServiceLevel,
    ServiceLevelPartNumber, SupportContract,
)

USD_TEMPLATE = '{% load humanize %}{% if value is not None %}${{ value|floatformat:2|intcomma }}{% endif %}'


class ServiceLevelTable(NetBoxTable):
    name = tables.Column(linkify=True)
    part_number_count = tables.Column(verbose_name='Part Numbers', orderable=False)
    tags = columns.TagColumn(url_name='plugins:netbox_tco:servicelevel_list')

    class Meta(NetBoxTable.Meta):
        model = ServiceLevel
        fields = ('pk', 'name', 'slug', 'description', 'part_number_count', 'tags')
        default_columns = ('name', 'slug', 'part_number_count', 'description')


class ServiceLevelPartNumberTable(tables.Table):
    part_number = tables.Column(linkify=False)
    manufacturer = tables.Column(linkify=True)

    class Meta:
        model = ServiceLevelPartNumber
        fields = ('part_number', 'manufacturer', 'description')
        empty_text = 'No part numbers defined.'


class LicenseTypeTable(NetBoxTable):
    name = tables.Column(linkify=True)
    part_number_count = tables.Column(verbose_name='Part Numbers', orderable=False)
    tags = columns.TagColumn(url_name='plugins:netbox_tco:licensetype_list')

    class Meta(NetBoxTable.Meta):
        model = LicenseType
        fields = ('pk', 'name', 'slug', 'description', 'part_number_count', 'tags')
        default_columns = ('name', 'slug', 'part_number_count')


class LicensePartNumberTable(tables.Table):
    part_number = tables.Column(linkify=False)
    manufacturer = tables.Column(linkify=True)

    class Meta:
        model = LicensePartNumber
        fields = ('part_number', 'manufacturer', 'description')
        empty_text = 'No part numbers defined.'


class QPITable(NetBoxTable):
    name = tables.Column(linkify=True)
    status = columns.ChoiceFieldColumn()
    tags = columns.TagColumn(url_name='plugins:netbox_tco:qpi_list')

    class Meta(NetBoxTable.Meta):
        model = QPI
        fields = ('pk', 'name', 'status', 'quote_requested', 'quote_received',
                  'quote_signed', 'ship_date', 'received_date', 'tags')
        default_columns = ('name', 'status', 'quote_requested', 'ship_date', 'received_date')


class LineItemTable(NetBoxTable):
    qpi = tables.Column(linkify=True)
    name = tables.Column(linkify=True)
    line_type = columns.ChoiceFieldColumn()
    line_total = tables.Column(verbose_name='Total', orderable=False)

    class Meta(NetBoxTable.Meta):
        model = LineItem
        fields = ('pk', 'qpi', 'name', 'line_type', 'quantity', 'unit_price', 'line_total',
                  'term_months', 'start_date')
        default_columns = ('qpi', 'name', 'line_type', 'quantity', 'unit_price', 'line_total')


class SupportContractTable(NetBoxTable):
    name = tables.Column(linkify=True)
    vendor = tables.Column(linkify=True)
    status = columns.ChoiceFieldColumn()
    renewal_status = columns.ChoiceFieldColumn()
    line_count = tables.Column(verbose_name='Lines')
    latest_end = columns.DateColumn(verbose_name='End date')
    tags = columns.TagColumn(url_name='plugins:netbox_tco:supportcontract_list')

    class Meta(NetBoxTable.Meta):
        model = SupportContract
        fields = ('pk', 'name', 'vendor', 'contract_id', 'status', 'renewal_status',
                  'line_count', 'latest_end', 'renewal_date', 'description', 'tags')
        default_columns = ('name', 'vendor', 'contract_id', 'status', 'line_count', 'latest_end',
                           'renewal_status')


class CoverageLineTable(NetBoxTable):
    id = tables.Column(linkify=True, verbose_name='ID')
    support_contract = tables.Column(linkify=True)
    assigned_object = tables.Column(linkify=True, orderable=False, verbose_name='Covered object')
    assigned_object_type = columns.ContentTypeColumn(verbose_name='Type')
    status = columns.ChoiceFieldColumn()
    service_level = tables.Column(linkify=True)
    funding_line_item = tables.Column(linkify=True, verbose_name='Funded by')
    price = columns.TemplateColumn(template_code=USD_TEMPLATE)
    tags = columns.TagColumn(url_name='plugins:netbox_tco:coverageline_list')

    class Meta(NetBoxTable.Meta):
        model = CoverageLine
        fields = ('pk', 'id', 'support_contract', 'assigned_object', 'assigned_object_type', 'status',
                  'service_level', 'funding_line_item', 'start_date', 'end_date', 'price', 'tags')
        default_columns = ('pk', 'id', 'support_contract', 'assigned_object', 'status', 'service_level',
                           'start_date', 'end_date', 'price')


class LicenseTable(NetBoxTable):
    vendor = tables.Column(linkify=True)
    status = columns.ChoiceFieldColumn()
    renewal_status = columns.ChoiceFieldColumn()
    tags = columns.TagColumn(url_name='plugins:netbox_tco:license_list')

    class Meta(NetBoxTable.Meta):
        model = License
        fields = ('pk', 'vendor', 'status', 'renewal_status', 'tags')
        default_columns = ('vendor', 'status', 'renewal_status')


class LicenseLineTable(tables.Table):
    device = tables.Column(linkify=True)
    license_type = tables.Column(linkify=True)
    billing_term = columns.ChoiceFieldColumn()

    class Meta:
        model = LicenseLine
        fields = ('device', 'license_type', 'billing_term', 'start_date', 'end_date',
                  'renewal_date', 'price')
        empty_text = 'No license lines.'


class LifecycleRecordTable(NetBoxTable):
    name = tables.Column(linkify=True)
    device_type_count = tables.Column(verbose_name='Device Types', orderable=False)
    tags = columns.TagColumn(url_name='plugins:netbox_tco:lifecyclerecord_list')

    class Meta(NetBoxTable.Meta):
        model = LifecycleRecord
        fields = ('pk', 'name', 'notice_date', 'device_type_count', 'tags')
        default_columns = ('name', 'notice_date', 'device_type_count')


class LifecycleMilestoneTable(tables.Table):
    class Meta:
        model = LifecycleMilestone
        fields = ('milestone_type', 'date')
        empty_text = 'No milestones defined.'
