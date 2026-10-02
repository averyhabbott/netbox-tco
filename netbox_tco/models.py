from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from netbox.models import NetBoxModel
from netbox.plugins import get_plugin_config

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
        limit_choices_to=models.Q(app_label='netbox_tco', model__in=['qpi', 'supportcontract', 'license']),
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
# Pillar 4 — Support Contracts
# ---------------------------------------------------------------------------

class SupportContract(NetBoxModel):
    name = models.CharField(max_length=200)
    vendor = models.ForeignKey(
        'dcim.Manufacturer',
        on_delete=models.PROTECT,
        related_name='netbox_tco_support_contracts',
    )
    contract_id = models.CharField(max_length=200, blank=True, verbose_name='Contract ID')
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
        help_text='Optional override. Leave blank to use the contract end date.',
    )
    predecessors = models.ManyToManyField(
        'self',
        symmetrical=False,
        blank=True,
        related_name='successors',
        verbose_name='Replaces',
    )
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        if self.contract_id:
            return f'{self.name} ({self.contract_id})'
        return self.name

    def get_absolute_url(self):
        return reverse('plugins:netbox_tco:supportcontract', args=[self.pk])

    def get_status_color(self):
        return ContractStatusChoices.colors.get(self.status)

    def get_renewal_status_color(self):
        return RenewalStatusChoices.colors.get(self.renewal_status)

    @property
    def start_date(self):
        return self.coverage_lines.aggregate(d=models.Min('start_date'))['d']

    @property
    def end_date(self):
        return self.coverage_lines.aggregate(d=models.Max('end_date'))['d']

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
        return self.coverage_lines.aggregate(t=models.Sum('price'))['t'] or 0

    @property
    def funding_line_items(self):
        return LineItem.objects.filter(coverage_lines__support_contract=self).distinct()

    def apply_status_transitions(self, today=None):
        """Pending → Active once started; an Active, started contract supersedes its predecessors."""
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


class CoverageLine(NetBoxModel):
    """One device or module covered by a support contract for one term."""
    support_contract = models.ForeignKey(
        SupportContract,
        on_delete=models.CASCADE,
        related_name='coverage_lines',
    )
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
    start_date = models.DateField()
    end_date = models.DateField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=50,
        choices=CoverageStatusChoices,
        default=CoverageStatusChoices.STATUS_PENDING,
        editable=False,
    )

    class Meta:
        ordering = ['support_contract', '-end_date', 'pk']
        indexes = [
            models.Index(fields=['assigned_object_type', 'assigned_object_id']),
        ]

    def __str__(self):
        if self.assigned_object:
            target = str(self.assigned_object)
        else:
            target = self.get_status_display()
        return f'{target} — {self.start_date} to {self.end_date}'

    def get_absolute_url(self):
        return reverse('plugins:netbox_tco:coverageline', args=[self.pk])

    def get_status_color(self):
        return CoverageStatusChoices.colors.get(self.status)

    def apply_funding_defaults(self):
        """Fill blank service level, dates, and price from the funding line item."""
        li = self.funding_line_item
        if not li:
            return
        if not self.service_level_id and li.support_sku_id:
            self.service_level = li.support_sku.service_level
        if not self.start_date and li.start_date:
            self.start_date = li.start_date
        if not self.end_date and li.end_date:
            self.end_date = li.end_date
        if self.price is None:
            self.price = li.unit_price

    def clean_fields(self, exclude=None):
        # Defaults must be in place before the required-field checks run
        self.apply_funding_defaults()
        super().clean_fields(exclude=exclude)

    def clean(self):
        super().clean()
        self.apply_funding_defaults()

        li = self.funding_line_item
        if li is not None:
            if li.line_type != LineItemTypeChoices.TYPE_SUPPORT:
                raise ValidationError({'funding_line_item': 'Must be a support line item.'})
            used = li.coverage_lines.exclude(pk=self.pk).count()
            if used >= li.quantity:
                raise ValidationError({
                    'funding_line_item':
                        f'This line item (qty {li.quantity}) already funds {used} coverage line(s).'
                })

        if self.assigned_object_type_id and (
            self.assigned_object_type.app_label, self.assigned_object_type.model
        ) not in [('dcim', m) for m in coverable_model_names()]:
            raise ValidationError('Coverage can only be assigned to a device or module.')

        if not self.service_level_id:
            raise ValidationError({'service_level': 'Required (or choose a funding line item with a support SKU).'})
        if not self.start_date:
            raise ValidationError({'start_date': 'Required (or set a start date on the funding line item).'})
        if not self.end_date:
            raise ValidationError({'end_date': 'Required (or set a term on the funding line item).'})
        if self.end_date < self.start_date:
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
# Pillar 5 — Licenses
# ---------------------------------------------------------------------------

class License(NetBoxModel):
    vendor = models.ForeignKey(
        'dcim.Manufacturer',
        on_delete=models.PROTECT,
        related_name='netbox_tco_licenses',
    )
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
    predecessors = models.ManyToManyField(
        'self',
        symmetrical=False,
        blank=True,
        related_name='successors',
    )
    funding_line_items = models.ManyToManyField(
        LineItem,
        blank=True,
        limit_choices_to={'line_type': LineItemTypeChoices.TYPE_LICENSE},
        related_name='netbox_tco_funded_licenses',
    )

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return f'License #{self.pk} — {self.vendor}'

    def get_absolute_url(self):
        return reverse('plugins:netbox_tco:license', args=[self.pk])


class LicenseLine(models.Model):
    license = models.ForeignKey(
        License,
        on_delete=models.CASCADE,
        related_name='license_lines',
    )
    device = models.ForeignKey(
        'dcim.Device',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='netbox_tco_license_lines',
    )
    license_type = models.ForeignKey(
        LicenseType,
        on_delete=models.PROTECT,
        related_name='license_lines',
    )
    billing_term = models.CharField(
        max_length=50,
        choices=BillingTermChoices,
        default=BillingTermChoices.TERM_SUBSCRIPTION,
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    renewal_date = models.DateField(null=True, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    license_key = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ['license', 'device']

    def __str__(self):
        device_str = str(self.device) if self.device else 'Pending'
        return f'{device_str} — {self.license_type}'

    def clean(self):
        super().clean()
        if self.billing_term == BillingTermChoices.TERM_SUBSCRIPTION:
            if not self.end_date:
                raise ValidationError({'end_date': 'Required for subscription licenses.'})
        if self.billing_term == BillingTermChoices.TERM_PERPETUAL:
            if self.end_date:
                raise ValidationError({'end_date': 'Perpetual licenses do not have an end date.'})
            if self.renewal_date:
                raise ValidationError({'renewal_date': 'Perpetual licenses do not have a renewal date.'})


# ---------------------------------------------------------------------------
# Pillar 6 — EOS/EOL
# ---------------------------------------------------------------------------

class LifecycleRecord(NetBoxModel):
    name = models.CharField(max_length=200)
    device_types = models.ManyToManyField(
        'dcim.DeviceType',
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

    def clean(self):
        super().clean()
        # Validate that each DeviceType appears in at most one LifecycleRecord.
        # M2M is validated post-save via a signal; cross-record uniqueness checked here
        # when editing existing records.
        if self.pk:
            qs = LifecycleRecord.objects.filter(
                device_types__in=self.device_types.all()
            ).exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError(
                    'One or more selected device types already belong to another lifecycle record.'
                )


class LifecycleMilestone(models.Model):
    lifecycle_record = models.ForeignKey(
        LifecycleRecord,
        on_delete=models.CASCADE,
        related_name='milestones',
    )
    milestone_type = models.CharField(max_length=200)
    date = models.DateField()

    class Meta:
        ordering = ['date']

    def __str__(self):
        return f'{self.milestone_type}: {self.date}'
