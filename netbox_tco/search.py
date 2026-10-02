from netbox.search import SearchIndex, register_search

from .models import (
    License, LicensePartNumber, LicenseType, LifecycleRecord,
    QPI, ServiceLevel, ServiceLevelPartNumber, SupportContract,
)


@register_search
class ServiceLevelIndex(SearchIndex):
    model = ServiceLevel
    fields = (
        ('name', 100),
        ('slug', 110),
        ('description', 500),
    )


@register_search
class ServiceLevelPartNumberIndex(SearchIndex):
    model = ServiceLevelPartNumber
    fields = (
        ('part_number', 100),
        ('description', 500),
    )


@register_search
class LicenseTypeIndex(SearchIndex):
    model = LicenseType
    fields = (
        ('name', 100),
        ('slug', 110),
        ('description', 500),
    )


@register_search
class LicensePartNumberIndex(SearchIndex):
    model = LicensePartNumber
    fields = (
        ('part_number', 100),
        ('description', 500),
    )


@register_search
class QPIIndex(SearchIndex):
    model = QPI
    fields = (
        ('name', 100),
    )


@register_search
class SupportContractIndex(SearchIndex):
    model = SupportContract
    fields = (
        ('name', 100),
        ('contract_id', 100),
        ('description', 500),
    )
    display_attrs = ('vendor', 'status')


@register_search
class LicenseIndex(SearchIndex):
    model = License
    fields = (
        ('name', 100),
        ('license_number', 100),
        ('description', 500),
    )
    display_attrs = ('vendor', 'status')


@register_search
class LifecycleRecordIndex(SearchIndex):
    model = LifecycleRecord
    fields = (
        ('name', 100),
    )
