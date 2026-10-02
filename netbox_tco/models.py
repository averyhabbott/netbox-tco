from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from netbox.models import NetBoxModel
from netbox.plugins import get_plugin_config
from utilities.fields import ColorField

from .choices import (
    BillingTermChoices, ContractStatusChoices, CoverageStatusChoices, LineItemTypeChoices,
    QPIStatusChoices, RenewalStatusChoices,
)
from .provisioning import (
    coverable_limit_choices_to, coverable_model_names, provisionable_limit_choices_to,
)

User = get_user_model()


# ---------------------------------------------------------------------------
# Pillar 1 — Controlled-vocabulary lookups
# ---------------------------------------------------------------------------

class ServiceLevel(NetBoxModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('plugins:netbox_tco:servicelevel', args=[self.pk])


class ServiceLevelPartNumber(models.Model):
    service_level = models.ForeignKey(
        ServiceLevel,
        on_delete=models.CASCADE,
        related_name='part_numbers',
    )
    part_number = models.CharField(max_length=200, unique=True)
    manufacturer = models.ForeignKey(
        'dcim.Manufacturer',
        on_delete=models.PROTECT,
        related_name='netbox_tco_service_level_part_numbers',
    )
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['part_number']

    def __str__(self):
        return self.part_number


class LicenseType(NetBoxModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('plugins:netbox_tco:licensetype', args=[self.pk])


class LicensePartNumber(models.Model):
    license_type = models.ForeignKey(
        LicenseType,
        on_delete=models.CASCADE,
        related_name='part_numbers',
    )
    part_number = models.CharField(max_length=200, unique=True)
    manufacturer = models.ForeignKey(
        'dcim.Manufacturer',
        on_delete=models.PROTECT,
        related_name='netbox_tco_license_part_numbers',
    )
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['part_number']

    def __str__(self):
        return self.part_number


# ---------------------------------------------------------------------------
# Pillar 2 — QPI + LineItem + Attachment
# ---------------------------------------------------------------------------

class QPI(NetBoxModel):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    owners = models.ManyToManyField(
        User,
        blank=True,
        related_name='netbox_tco_owned_qpis',
    )
    status = models.CharField(
        max_length=50,
        choices=QPIStatusChoices,
        default=QPIStatusChoices.STATUS_REQUESTED,
    )
    quote_requested = models.DateField(null=True, blank=True)
    quote_received = models.DateField(null=True, blank=True)
    quote_signed = models.DateField(null=True, blank=True)
    quote_returned = models.DateField(null=True, blank=True)
    auto_populate_returned = models.BooleanField(
        default=True,
        help_text='Automatically set Quote Returned date when Quote Signed is set',
    )
    ship_date = models.DateField(null=True, blank=True)
    received_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-created']
        verbose_name = 'QPI'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('plugins:netbox_tco:qpi', args=[self.pk])

    def get_status_color(self):
        return QPIStatusChoices.colors.get(self.status)

    def save(self, *args, **kwargs):
        import datetime
        if self.auto_populate_returned and self.quote_signed and not self.quote_returned:
            self.quote_returned = self.quote_signed

        # Auto-advance status based on the latest stage date set.
        # Cancelled and Lost are terminal — never overridden by auto-advance.
        # ship_date and received_date only advance status when they are today or past
        # (future dates represent planned dates and should not trigger a status change).
        terminal = (QPIStatusChoices.STATUS_CANCELLED, QPIStatusChoices.STATUS_LOST)
        if self.status not in terminal:
            today = datetime.date.today()
            if self.received_date and self.received_date <= today:
                self.status = QPIStatusChoices.STATUS_COMPLETE
            elif self.ship_date and self.ship_date <= today:
                self.status = QPIStatusChoices.STATUS_SHIPPED
            elif self.quote_returned:
                self.status = QPIStatusChoices.STATUS_RETURNED
            elif self.quote_signed:
                self.status = QPIStatusChoices.STATUS_SIGNED
            elif self.quote_received:
                self.status = QPIStatusChoices.STATUS_RECEIVED
            elif self.quote_requested:
                self.status = QPIStatusChoices.STATUS_REQUESTED

        super().save(*args, **kwargs)


class LineItem(NetBoxModel):
    qpi = models.ForeignKey(
        QPI,
        on_delete=models.CASCADE,
        related_name='line_items',
    )
    line_type = models.CharField(
        max_length=50,
        choices=LineItemTypeChoices,
    )
    device_type = models.ForeignKey(
        'dcim.DeviceType',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='netbox_tco_line_items',
    )
    module_type = models.ForeignKey(
        'dcim.ModuleType',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='netbox_tco_line_items',
    )
    rack_type = models.ForeignKey(
        'dcim.RackType',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='netbox_tco_line_items',
    )
    support_sku = models.ForeignKey(
        ServiceLevelPartNumber,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='line_items',
    )
    license_sku = models.ForeignKey(
        LicensePartNumber,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='line_items',
    )
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    term_months = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Term length in months (support/license only)',
    )
    start_date = models.DateField(
        null=True,
        blank=True,
        help_text='Start date (support/license only)',
    )
    name = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['qpi', 'line_type']

    def __str__(self):
        if self.name:
            return f'{self.qpi} - {self.name}'
        ref = self.device_type or self.module_type or self.rack_type or self.support_sku or self.license_sku
        return f'{self.qpi} - {ref}' if ref else f'{self.qpi} - {self.get_line_type_display()}'

    def get_absolute_url(self):
        return reverse('plugins:netbox_tco:lineitem', args=[self.pk])

    def get_line_type_color(self):
        return LineItemTypeChoices.colors.get(self.line_type)

    @property
    def line_total(self):
        return self.quantity * self.unit_price

    @property
    def end_date(self):
        if self.start_date and self.term_months:
            from dateutil.relativedelta import relativedelta
            return self.start_date + relativedelta(months=self.term_months)
        return None

    def clean(self):
        super().clean()
        if self.line_type == LineItemTypeChoices.TYPE_HARDWARE:
            hw_refs = [self.device_type, self.module_type, self.rack_type]
            set_count = sum(1 for r in hw_refs if r is not None)
            if set_count == 0:
                raise ValidationError('Hardware line items must reference a Device Type, Module Type, or Rack Type.')
            if set_count > 1:
                raise ValidationError('Hardware line items must reference exactly one of Device Type, Module Type, or Rack Type.')
            if self.support_sku or self.license_sku:
                raise ValidationError('Hardware line items must not reference a SKU.')
        elif self.line_type == LineItemTypeChoices.TYPE_SUPPORT:
            if not self.support_sku:
                raise ValidationError({'support_sku': 'Required for support line items.'})
            if self.device_type or self.module_type or self.rack_type or self.license_sku:
                raise ValidationError('Support line items must only reference a support SKU.')
        elif self.line_type == LineItemTypeChoices.TYPE_LICENSE:
            if not self.license_sku:
                raise ValidationError({'license_sku': 'Required for license line items.'})
            if self.device_type or self.module_type or self.rack_type or self.support_sku:
                raise ValidationError('License line items must only reference a license SKU.')


class ProvisionedItem(models.Model):
    """
    Links a hardware LineItem to a single provisioned object (Device, Module, or Rack).
    Populated automatically via post_save signal when the tco_line_item custom field is set.
    One record per object — a device/module/rack has exactly one source line item.
    """
    line_item = models.ForeignKey(
        LineItem,
        on_delete=models.CASCADE,
        related_name='provisioned_items',
    )
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to=provisionable_limit_choices_to(),
    )
    object_id = models.PositiveBigIntegerField()
    target = GenericForeignKey('content_type', 'object_id')

    class Meta:
        unique_together = ('content_type', 'object_id')
        ordering = ['content_type', 'object_id']

    def __str__(self):
        return f'{self.target} → {self.line_item}'


def attachment_upload_path(instance, filename):
    return f'netbox_tco/attachments/{instance.content_type.app_label}/{instance.object_id}/{filename}'


class Attachment(models.Model):
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to=models.Q(
            app_label='netbox_tco', model__in=['qpi', 'supportcontract', 'license', 'lifecyclerecord'],
        ),
    )
    object_id = models.PositiveBigIntegerField()
    parent = GenericForeignKey(ct_field='content_type', fk_field='object_id')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    document_type = models.CharField(max_length=100)
    file = models.FileField(upload_to=attachment_upload_path)
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        editable=False,
    )
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return self.name

    def delete(self, *args, **kwargs):
        path = self.file.name
        super().delete(*args, **kwargs)
        self.file.storage.delete(path)


# ---------------------------------------------------------------------------
# Pillars 4 & 5 — shared bases for Support Contracts and Licenses
# ---------------------------------------------------------------------------

class ContractBase(NetBoxModel):
    """
    A durable contract (SupportContract) or License. Its dated lines carry the cost;
    start, end, total, expiry, and funding line items are all derived from them.
    """
    name = models.CharField(max_length=200)
    status = models.CharField(
        max_length=50,
        choices=ContractStatusChoices,
        default=ContractStatusChoices.STATUS_ACTIVE,
    )
    renewal_status = models.CharField(
        max_length=50,
        choices=RenewalStatusChoices,
        default=RenewalStatusChoices.STATUS_OK,
        editable=False,
    )
    renewal_date = models.DateField(
        null=True,
        blank=True,
        help_text='Optional override. Leave blank to use the latest end date of its lines.',
    )
    predecessors = models.ManyToManyField(
        'self',
        symmetrical=False,
        blank=True,
        related_name='successors',
        verbose_name='Replaces',
    )
    description = models.TextField(blank=True)

    # Set by subclasses
    lines_attr = None       # reverse accessor for the child lines
    reference_attr = None   # vendor reference number field

    class Meta:
        abstract = True

    def __str__(self):
        reference = getattr(self, self.reference_attr)
        if reference:
            return f'{self.name} ({reference})'
        return self.name

    def get_status_color(self):
        return ContractStatusChoices.colors.get(self.status)

    def get_renewal_status_color(self):
        return RenewalStatusChoices.colors.get(self.renewal_status)

    @property
    def lines(self):
        return getattr(self, self.lines_attr)

    @property
    def start_date(self):
        return self.lines.aggregate(d=models.Min('start_date'))['d']

    @property
    def end_date(self):
        # Perpetual license lines have no end date and are ignored by Max()
        return self.lines.aggregate(d=models.Max('end_date'))['d']

    @property
    def effective_renewal_date(self):
        return self.renewal_date or self.end_date

    @property
    def is_expired(self):
        from datetime import date
        end = self.end_date
        return end is not None and end < date.today()

    @property
    def total_price(self):
        return self.lines.aggregate(t=models.Sum('price'))['t'] or 0

    @property
    def funding_line_items(self):
        return LineItem.objects.filter(pk__in=self.lines.values('funding_line_item'))

    def apply_status_transitions(self, today=None):
        """Pending → Active once started; an Active, started record supersedes its predecessors."""
        from datetime import date
        today = today or date.today()
        start = self.start_date
        if start is None or start > today:
            return
        if self.status == ContractStatusChoices.STATUS_PENDING:
            self.snapshot()
            self.status = ContractStatusChoices.STATUS_ACTIVE
            self.save()
        if self.status == ContractStatusChoices.STATUS_ACTIVE:
            for predecessor in self.predecessors.filter(status__in=(
                ContractStatusChoices.STATUS_PENDING, ContractStatusChoices.STATUS_ACTIVE,
            )):
                predecessor.snapshot()
                predecessor.status = ContractStatusChoices.STATUS_SUPERSEDED
                predecessor.save()


class ContractLineBase(NetBoxModel):
    """One device or module on a contract or License for one term. Unassigned = pending."""
    assigned_object_type = models.ForeignKey(
        ContentType,
        on_delete=models.PROTECT,
        limit_choices_to=coverable_limit_choices_to(),
        null=True,
        blank=True,
        related_name='+',
    )
    assigned_object_id = models.PositiveBigIntegerField(null=True, blank=True)
    assigned_object = GenericForeignKey('assigned_object_type', 'assigned_object_id')
    start_date = models.DateField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=50,
        choices=CoverageStatusChoices,
        default=CoverageStatusChoices.STATUS_PENDING,
        editable=False,
    )

    # Set by subclasses
    parent_attr = None          # FK to the contract / License
    funding_line_type = None    # LineItem.line_type that can fund this line
    sku_attr = None             # LineItem SKU field for this line type

    class Meta:
        abstract = True

    def __str__(self):
        target = str(self.assigned_object) if self.assigned_object else self.get_status_display()
        if self.end_date:
            return f'{target} — {self.start_date} to {self.end_date}'
        return f'{target} — from {self.start_date}'

    @property
    def parent(self):
        return getattr(self, self.parent_attr)

    def get_status_color(self):
        return CoverageStatusChoices.colors.get(self.status)

    def has_end_date(self):
        return True

    def apply_type_defaults(self, line_item):
        """Fill the type-specific reference (service level / license type) from the funding SKU."""
        raise NotImplementedError

    def apply_funding_defaults(self):
        """Fill blank type, dates, and price from the funding line item."""
        li = self.funding_line_item
        if not li:
            return
        self.apply_type_defaults(li)
        if not self.start_date and li.start_date:
            self.start_date = li.start_date
        if self.has_end_date() and not self.end_date and li.end_date:
            self.end_date = li.end_date
        if self.price is None:
            self.price = li.unit_price

    def clean_fields(self, exclude=None):
        # Defaults must be in place before the required-field checks run
        self.apply_funding_defaults()
        super().clean_fields(exclude=exclude)

    def clean_terms(self):
        """Type-specific required-field checks."""

    def clean(self):
        super().clean()
        self.apply_funding_defaults()

        li = self.funding_line_item
        if li is not None:
            if li.line_type != self.funding_line_type:
                raise ValidationError({
                    'funding_line_item': f'Must be a {self.funding_line_type} line item.'
                })
            used = type(self).objects.filter(funding_line_item=li).exclude(pk=self.pk).count()
            if used >= li.quantity:
                raise ValidationError({
                    'funding_line_item':
                        f'This line item (qty {li.quantity}) already funds {used} line(s).'
                })

        if self.assigned_object_type_id and (
            self.assigned_object_type.app_label, self.assigned_object_type.model
        ) not in [('dcim', m) for m in coverable_model_names()]:
            raise ValidationError('Only a device or module can be assigned.')

        if not self.start_date:
            raise ValidationError({'start_date': 'Required (or set a start date on the funding line item).'})
        self.clean_terms()
        if self.end_date and self.end_date < self.start_date:
            raise ValidationError({'end_date': 'End date must be on or after the start date.'})
        if self.price is None:
            raise ValidationError({'price': 'Required (or choose a funding line item).'})

    def save(self, *args, **kwargs):
        if self.assigned_object_id:
            self.status = CoverageStatusChoices.STATUS_ASSIGNED
        elif self.status != CoverageStatusChoices.STATUS_RETIRED:
            self.status = CoverageStatusChoices.STATUS_PENDING
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# Pillar 4 — Support Contracts
# ---------------------------------------------------------------------------

class SupportContract(ContractBase):
    vendor = models.ForeignKey(
        'dcim.Manufacturer',
        on_delete=models.PROTECT,
        related_name='netbox_tco_support_contracts',
    )
    contract_id = models.CharField(max_length=200, blank=True, verbose_name='Contract ID')

    lines_attr = 'coverage_lines'
    reference_attr = 'contract_id'

    class Meta:
        ordering = ['name']

    def get_absolute_url(self):
        return reverse('plugins:netbox_tco:supportcontract', args=[self.pk])


class CoverageLine(ContractLineBase):
    """One device or module covered by a support contract for one term."""
    support_contract = models.ForeignKey(
        SupportContract,
        on_delete=models.CASCADE,
        related_name='coverage_lines',
    )
    funding_line_item = models.ForeignKey(
        LineItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'line_type': LineItemTypeChoices.TYPE_SUPPORT},
        related_name='coverage_lines',
    )
    service_level = models.ForeignKey(
        ServiceLevel,
        on_delete=models.PROTECT,
        related_name='coverage_lines',
    )
    end_date = models.DateField()

    parent_attr = 'support_contract'
    funding_line_type = LineItemTypeChoices.TYPE_SUPPORT
    sku_attr = 'support_sku'

    class Meta:
        ordering = ['support_contract', '-end_date', 'pk']
        indexes = [
            models.Index(fields=['assigned_object_type', 'assigned_object_id']),
        ]

    def get_absolute_url(self):
        return reverse('plugins:netbox_tco:coverageline', args=[self.pk])

    def apply_type_defaults(self, line_item):
        if not self.service_level_id and line_item.support_sku_id:
            self.service_level = line_item.support_sku.service_level

    def clean_terms(self):
        if not self.service_level_id:
            raise ValidationError({'service_level': 'Required (or choose a funding line item with a support SKU).'})
        if not self.end_date:
            raise ValidationError({'end_date': 'Required (or set a term on the funding line item).'})


# ---------------------------------------------------------------------------
# Pillar 5 — Licenses
# ---------------------------------------------------------------------------

LICENSE_KEY_MASK = '********'


class License(ContractBase):
    vendor = models.ForeignKey(
        'dcim.Manufacturer',
        on_delete=models.PROTECT,
        related_name='netbox_tco_licenses',
    )
    license_number = models.CharField(
        max_length=200,
        blank=True,
        help_text='Vendor subscription, entitlement, or agreement number.',
    )

    lines_attr = 'license_lines'
    reference_attr = 'license_number'

    class Meta:
        ordering = ['name']

    def get_absolute_url(self):
        return reverse('plugins:netbox_tco:license', args=[self.pk])


class LicenseLine(ContractLineBase):
    """One device or module licensed for one term (subscription) or from a start date (perpetual)."""
    license = models.ForeignKey(
        License,
        on_delete=models.CASCADE,
        related_name='license_lines',
    )
    funding_line_item = models.ForeignKey(
        LineItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'line_type': LineItemTypeChoices.TYPE_LICENSE},
        related_name='license_lines',
    )
    license_type = models.ForeignKey(
        LicenseType,
        on_delete=models.PROTECT,
        related_name='license_lines',
    )
    billing_term = models.CharField(
        max_length=50,
        choices=BillingTermChoices,
        blank=True,
        help_text='Leave blank to infer from the funding line item (a term means subscription).',
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text='Subscription only.',
    )
    license_key = models.CharField(
        max_length=500,
        blank=True,
        help_text='Shown on this page; masked in the change log.',
    )

    parent_attr = 'license'
    funding_line_type = LineItemTypeChoices.TYPE_LICENSE
    sku_attr = 'license_sku'

    class Meta:
        ordering = ['license', '-start_date', 'pk']
        indexes = [
            models.Index(fields=['assigned_object_type', 'assigned_object_id']),
        ]

    def get_absolute_url(self):
        return reverse('plugins:netbox_tco:licenseline', args=[self.pk])

    def get_billing_term_color(self):
        return BillingTermChoices.colors.get(self.billing_term)

    def has_end_date(self):
        return self.billing_term == BillingTermChoices.TERM_SUBSCRIPTION

    def apply_type_defaults(self, line_item):
        if not self.license_type_id and line_item.license_sku_id:
            self.license_type = line_item.license_sku.license_type
        if not self.billing_term:
            self.billing_term = (BillingTermChoices.TERM_SUBSCRIPTION if line_item.term_months
                                 else BillingTermChoices.TERM_PERPETUAL)

    def clean_terms(self):
        if not self.license_type_id:
            raise ValidationError({'license_type': 'Required (or choose a funding line item with a license SKU).'})
        if not self.billing_term:
            raise ValidationError({'billing_term': 'Required (or choose a funding line item).'})
        if self.billing_term == BillingTermChoices.TERM_SUBSCRIPTION and not self.end_date:
            raise ValidationError({'end_date': 'Required for subscriptions (or set a term on the funding line item).'})
        if self.billing_term == BillingTermChoices.TERM_PERPETUAL and self.end_date:
            raise ValidationError({'end_date': 'Perpetual licenses do not have an end date.'})

    def serialize_object(self, exclude=None):
        # Keeps license keys out of the change log and event-rule snapshots
        data = super().serialize_object(exclude=exclude)
        if data.get('license_key'):
            data['license_key'] = LICENSE_KEY_MASK
        return data


# ---------------------------------------------------------------------------
# Pillar 6 — EOS/EOL
# ---------------------------------------------------------------------------

class MilestoneType(NetBoxModel):
    """Controlled vocabulary for lifecycle milestones (End of Sale, End of Support, ...)."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    color = ColorField(default='9e9e9e')
    weight = models.PositiveSmallIntegerField(
        default=100,
        help_text='Display order in dropdowns and lists (lower first).',
    )
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['weight', 'name']
        verbose_name = 'EOx milestone'
        verbose_name_plural = 'EOx milestones'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('plugins:netbox_tco:milestonetype', args=[self.pk])


class LifecycleRecord(NetBoxModel):
    """
    One vendor end-of-life notice. Device and module types each appear on at most one record,
    so the dates shown for any device or module are unambiguous. The vendor is derived from the
    attached types (same idea as part numbers).
    """
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    device_types = models.ManyToManyField(
        'dcim.DeviceType',
        blank=True,
        related_name='netbox_tco_lifecycle_records',
    )
    module_types = models.ManyToManyField(
        'dcim.ModuleType',
        blank=True,
        related_name='netbox_tco_lifecycle_records',
    )
    reference_url = models.URLField(blank=True)
    notice_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('plugins:netbox_tco:lifecyclerecord', args=[self.pk])

    @property
    def manufacturers(self):
        from dcim.models import Manufacturer
        return Manufacturer.objects.filter(
            models.Q(device_types__netbox_tco_lifecycle_records=self) |
            models.Q(module_types__netbox_tco_lifecycle_records=self)
        ).distinct()

    @classmethod
    def type_conflicts(cls, device_types=(), module_types=(), exclude_pk=None):
        """
        Return error messages for any of the given types already on another record.
        Checked in the form and API serializer, since M2M values aren't saved yet when clean() runs.
        """
        errors = []
        for field, types in (('device_types', device_types), ('module_types', module_types)):
            others = cls.objects.filter(**{f'{field}__in': types})
            if exclude_pk:
                others = others.exclude(pk=exclude_pk)
            for record in others.distinct().prefetch_related(field):
                taken = sorted(str(t) for t in getattr(record, field).all() if t in types)
                errors.append(f'{", ".join(taken)} already on lifecycle record "{record}".')
        return errors

    @staticmethod
    def for_type(type_obj):
        """The record covering a DeviceType or ModuleType, or None."""
        if type_obj is None:
            return None
        return type_obj.netbox_tco_lifecycle_records.prefetch_related('milestones__milestone_type').first()


class LifecycleMilestone(models.Model):
    lifecycle_record = models.ForeignKey(
        LifecycleRecord,
        on_delete=models.CASCADE,
        related_name='milestones',
    )
    milestone_type = models.ForeignKey(
        MilestoneType,
        on_delete=models.PROTECT,
        related_name='milestones',
    )
    date = models.DateField()

    class Meta:
        ordering = ['date', 'milestone_type__weight']
        constraints = [
            models.UniqueConstraint(
                fields=['lifecycle_record', 'milestone_type'],
                name='netbox_tco_milestone_unique_type_per_record',
            ),
        ]

    def __str__(self):
        return f'{self.milestone_type}: {self.date}'
