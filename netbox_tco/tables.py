import django_tables2 as tables
from netbox.tables import NetBoxTable, columns

from .models import (
    CoverageLine, License, LicenseLine, LicensePartNumber, LicenseType,
    LifecycleMilestone, LifecycleRecord, LineItem, MilestoneType, QPI, ServiceLevel,
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
    name = tables.Column(linkify=True)
    vendor = tables.Column(linkify=True)
    status = columns.ChoiceFieldColumn()
    renewal_status = columns.ChoiceFieldColumn()
    line_count = tables.Column(verbose_name='Lines')
    latest_end = columns.DateColumn(verbose_name='End date')
    tags = columns.TagColumn(url_name='plugins:netbox_tco:license_list')

    class Meta(NetBoxTable.Meta):
        model = License
        fields = ('pk', 'name', 'vendor', 'license_number', 'status', 'renewal_status',
                  'line_count', 'latest_end', 'renewal_date', 'description', 'tags')
        default_columns = ('name', 'vendor', 'license_number', 'status', 'line_count', 'latest_end',
                           'renewal_status')


class LicenseLineTable(NetBoxTable):
    id = tables.Column(linkify=True, verbose_name='ID')
    license = tables.Column(linkify=True)
    assigned_object = tables.Column(linkify=True, orderable=False, verbose_name='Licensed object')
    assigned_object_type = columns.ContentTypeColumn(verbose_name='Type')
    status = columns.ChoiceFieldColumn()
    license_type = tables.Column(linkify=True)
    billing_term = columns.ChoiceFieldColumn(verbose_name='Term')
    funding_line_item = tables.Column(linkify=True, verbose_name='Funded by')
    price = columns.TemplateColumn(template_code=USD_TEMPLATE)
    tags = columns.TagColumn(url_name='plugins:netbox_tco:licenseline_list')

    class Meta(NetBoxTable.Meta):
        model = LicenseLine
        fields = ('pk', 'id', 'license', 'assigned_object', 'assigned_object_type', 'status',
                  'license_type', 'billing_term', 'funding_line_item', 'start_date', 'end_date',
                  'price', 'tags')
        default_columns = ('pk', 'id', 'license', 'assigned_object', 'status', 'license_type',
                           'billing_term', 'start_date', 'end_date', 'price')


class MilestoneTypeTable(NetBoxTable):
    name = tables.Column(linkify=True)
    color = columns.ColorColumn()
    milestone_count = tables.Column(verbose_name='Used On')
    tags = columns.TagColumn(url_name='plugins:netbox_tco:milestonetype_list')

    class Meta(NetBoxTable.Meta):
        model = MilestoneType
        fields = ('pk', 'id', 'name', 'slug', 'color', 'weight', 'description', 'milestone_count', 'tags')
        default_columns = ('pk', 'name', 'color', 'weight', 'milestone_count', 'description')


class LifecycleRecordTable(NetBoxTable):
    name = tables.Column(linkify=True)
    vendors = columns.TemplateColumn(
        template_code='{% for m in record.manufacturers %}<a href="{{ m.get_absolute_url }}">{{ m }}</a>'
                      '{% if not forloop.last %}, {% endif %}{% endfor %}',
        orderable=False,
        verbose_name='Vendor',
    )
    device_type_count = tables.Column(verbose_name='Device Types')
    module_type_count = tables.Column(verbose_name='Module Types')
    rack_type_count = tables.Column(verbose_name='Rack Types')
    milestones = columns.TemplateColumn(
        template_code='{% load builtins.filters %}{% for m in record.milestones.all %}'
                      '<span class="badge" style="color: #{{ m.milestone_type.color|fgcolor }}; '
                      'background-color: #{{ m.milestone_type.color }}">{{ m.milestone_type }}</span> {{ m.date }}'
                      '{% if not forloop.last %}<br>{% endif %}{% endfor %}',
        orderable=False,
        verbose_name='Milestones',
    )
    reference_url = tables.TemplateColumn(
        template_code='{% if value %}<a href="{{ value }}" target="_blank" rel="noopener">Link</a>{% endif %}',
        verbose_name='Reference',
    )
    tags = columns.TagColumn(url_name='plugins:netbox_tco:lifecyclerecord_list')

    class Meta(NetBoxTable.Meta):
        model = LifecycleRecord
        fields = ('pk', 'id', 'name', 'vendors', 'description', 'notice_date', 'device_type_count',
                  'module_type_count', 'rack_type_count', 'milestones', 'reference_url', 'tags')
        default_columns = ('pk', 'name', 'vendors', 'notice_date', 'device_type_count', 'module_type_count',
                           'rack_type_count', 'milestones')


class LifecycleMilestoneTable(tables.Table):
    class Meta:
        model = LifecycleMilestone
        fields = ('milestone_type', 'date')
        empty_text = 'No milestones defined.'
