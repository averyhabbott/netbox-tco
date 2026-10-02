from django import forms
from django.db.models import Count, Q
from dcim.models import Device, DeviceType, Manufacturer, Module, ModuleType, RackType
from netbox.forms import NetBoxModelBulkEditForm, NetBoxModelForm, NetBoxModelFilterSetForm
from utilities.forms import add_blank_choice
from utilities.forms.fields import DynamicModelChoiceField, DynamicModelMultipleChoiceField, SlugField
from utilities.forms.rendering import FieldSet

from .choices import (
    BillingTermChoices, ContractStatusChoices, CoverageStatusChoices, LineItemTypeChoices,
    QPIStatusChoices,
)
from .models import (
    Attachment, CoverageLine, License, LicenseLine, LicensePartNumber, LicenseType,
    LifecycleMilestone, LifecycleRecord, LineItem, MilestoneType, QPI, ServiceLevel,
    ServiceLevelPartNumber, SupportContract,
)


# ---------------------------------------------------------------------------
# Service Levels
# ---------------------------------------------------------------------------

class ServiceLevelForm(NetBoxModelForm):
    slug = SlugField()

    fieldsets = (
        FieldSet('name', 'slug', 'description', name='Service Level'),
        FieldSet('tags', name='Tags'),
    )

    class Meta:
        model = ServiceLevel
        fields = ('name', 'slug', 'description', 'tags')


class ServiceLevelFilterForm(NetBoxModelFilterSetForm):
    model = ServiceLevel
    manufacturer_id = DynamicModelMultipleChoiceField(
        queryset=Manufacturer.objects.all(),
        required=False,
        label='Manufacturer',
    )
    part_number = forms.CharField(required=False, label='Part number')


# ---------------------------------------------------------------------------
# License Types
# ---------------------------------------------------------------------------

class LicenseTypeForm(NetBoxModelForm):
    slug = SlugField()

    fieldsets = (
        FieldSet('name', 'slug', 'description', name='License Type'),
        FieldSet('tags', name='Tags'),
    )

    class Meta:
        model = LicenseType
        fields = ('name', 'slug', 'description', 'tags')


class LicenseTypeFilterForm(NetBoxModelFilterSetForm):
    model = LicenseType
    manufacturer_id = DynamicModelMultipleChoiceField(
        queryset=Manufacturer.objects.all(),
        required=False,
        label='Manufacturer',
    )
    part_number = forms.CharField(required=False, label='Part number')


# ---------------------------------------------------------------------------
# Part Numbers (inline; not standalone NetBoxModel forms)
# ---------------------------------------------------------------------------

class ServiceLevelPartNumberForm(forms.ModelForm):
    manufacturer = DynamicModelChoiceField(queryset=Manufacturer.objects.all())

    class Meta:
        model = ServiceLevelPartNumber
        fields = ('part_number', 'manufacturer', 'description')


class LicensePartNumberForm(forms.ModelForm):
    manufacturer = DynamicModelChoiceField(queryset=Manufacturer.objects.all())

    class Meta:
        model = LicensePartNumber
        fields = ('part_number', 'manufacturer', 'description')


# ---------------------------------------------------------------------------
# QPI
# ---------------------------------------------------------------------------

class QPIForm(NetBoxModelForm):
    fieldsets = (
        FieldSet('name', 'status', 'owners', 'description', name='General'),
        FieldSet('quote_requested', 'quote_received', 'quote_signed',
                 'auto_populate_returned', 'quote_returned',
                 name='Quote Dates'),
        FieldSet('ship_date', 'received_date', name='Shipping'),
        FieldSet('tags', name='Tags'),
    )

    class Meta:
        model = QPI
        fields = ('name', 'description', 'status', 'owners', 'quote_requested', 'quote_received',
                  'quote_signed', 'auto_populate_returned', 'quote_returned',
                  'ship_date', 'received_date', 'tags')
        widgets = {
            'quote_requested': forms.DateInput(attrs={'type': 'date'}),
            'quote_received': forms.DateInput(attrs={'type': 'date'}),
            'quote_signed': forms.DateInput(attrs={'type': 'date'}),
            'quote_returned': forms.DateInput(attrs={'type': 'date'}),
            'ship_date': forms.DateInput(attrs={'type': 'date'}),
            'received_date': forms.DateInput(attrs={'type': 'date'}),
        }


class QPIFilterForm(NetBoxModelFilterSetForm):
    model = QPI
    status = forms.MultipleChoiceField(
        choices=QPIStatusChoices,
        required=False,
    )


# ---------------------------------------------------------------------------
# Line Items
# ---------------------------------------------------------------------------

class LineItemForm(NetBoxModelForm):
    device_type = DynamicModelChoiceField(
        queryset=DeviceType.objects.all(),
        required=False,
        label='Device type',
    )
    module_type = DynamicModelChoiceField(
        queryset=ModuleType.objects.all(),
        required=False,
        label='Module type',
    )
    rack_type = DynamicModelChoiceField(
        queryset=RackType.objects.all(),
        required=False,
        label='Rack type',
    )
    support_sku = DynamicModelChoiceField(
        queryset=ServiceLevelPartNumber.objects.all(),
        required=False,
        label='Support SKU',
    )
    license_sku = DynamicModelChoiceField(
        queryset=LicensePartNumber.objects.all(),
        required=False,
        label='License SKU',
    )

    fieldsets = (
        FieldSet('qpi', 'line_type', 'name', name='General'),
        FieldSet('device_type', 'module_type', 'rack_type', 'support_sku', 'license_sku', name='Reference'),
        FieldSet('quantity', 'unit_price', 'term_months', 'start_date', name='Pricing'),
        FieldSet('description', name='Details'),
        FieldSet('tags', name='Tags'),
    )

    class Meta:
        model = LineItem
        fields = ('qpi', 'line_type', 'name', 'device_type', 'module_type', 'rack_type',
                  'support_sku', 'license_sku',
                  'quantity', 'unit_price', 'term_months', 'start_date', 'description', 'tags')
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
        }


class LineItemFilterForm(NetBoxModelFilterSetForm):
    model = LineItem
    line_type = forms.MultipleChoiceField(
        choices=LineItemTypeChoices,
        required=False,
    )


# ---------------------------------------------------------------------------
# Support Contracts & Licenses — shared pieces
# ---------------------------------------------------------------------------

REPLACES_HELP = 'Only when the vendor issued a new number or records were merged.'


class ContractFormMixin:
    def clean_predecessors(self):
        predecessors = self.cleaned_data['predecessors']
        if self.instance.pk and self.instance in predecessors:
            raise forms.ValidationError('A record cannot replace itself.')
        return predecessors


class AssignedObjectFormMixin:
    """Device / module pickers mapped onto a line's generic assigned_object."""

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        initial = kwargs.get('initial', {}).copy()
        if instance and instance.assigned_object:
            initial[instance.assigned_object_type.model] = instance.assigned_object
        kwargs['initial'] = initial
        super().__init__(*args, **kwargs)

    def clean(self):
        super().clean()
        device = self.cleaned_data.get('device')
        module = self.cleaned_data.get('module')
        if device and module:
            raise forms.ValidationError('Choose a device or a module, not both.')
        self.instance.assigned_object = device or module or None
        if self.instance.assigned_object is None:
            self.instance.assigned_object_type = None
            self.instance.assigned_object_id = None
        return self.cleaned_data


class LineQuantityFormMixin:
    """Add page only: a quantity that creates that many identical (pending) lines in one go."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            del self.fields['quantity']

    def clean(self):
        super().clean()
        quantity = self.cleaned_data.get('quantity') or 1
        if quantity > 1:
            if self.instance.assigned_object is not None:
                raise forms.ValidationError({
                    'quantity': 'Leave the device and module blank to add more than one line.'
                })
            li = self.cleaned_data.get('funding_line_item')
            if li is not None:
                used = type(self.instance).objects.filter(funding_line_item=li).count()
                if used + quantity > li.quantity:
                    raise forms.ValidationError({
                        'quantity': f'{li} (qty {li.quantity}) already funds {used} line(s); '
                                    f'only {max(li.quantity - used, 0)} more can be added.'
                    })
        return self.cleaned_data

    def save(self, *args, **kwargs):
        obj = super().save(*args, **kwargs)
        model = type(obj)
        for _ in range((self.cleaned_data.get('quantity') or 1) - 1):
            extra = model.objects.get(pk=obj.pk)
            extra.pk = None
            extra._state.adding = True
            extra.save()
            extra.tags.set(obj.tags.all())
        return obj


def _quantity_field():
    return forms.IntegerField(
        min_value=1, max_value=1000, initial=1,
        help_text='Number of identical lines to add. More than 1 creates pending lines (no device or module).',
    )


def _device_field():
    return DynamicModelChoiceField(queryset=Device.objects.all(), required=False, selector=True)


def _module_field():
    return DynamicModelChoiceField(queryset=Module.objects.all(), required=False, selector=True)


def _date_field(help_text=''):
    return forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}), help_text=help_text)


def _price_field(help_text=''):
    return forms.DecimalField(required=False, max_digits=12, decimal_places=2, help_text=help_text)


# ---------------------------------------------------------------------------
# Support Contracts
# ---------------------------------------------------------------------------

class SupportContractForm(ContractFormMixin, NetBoxModelForm):
    vendor = DynamicModelChoiceField(queryset=Manufacturer.objects.all())
    predecessors = DynamicModelMultipleChoiceField(
        queryset=SupportContract.objects.all(),
        required=False,
        label='Replaces',
        help_text=REPLACES_HELP,
    )

    fieldsets = (
        FieldSet('name', 'vendor', 'contract_id', 'status', 'description', name='Support Contract'),
        FieldSet('renewal_date', 'predecessors', name='Renewal'),
        FieldSet('tags', name='Tags'),
    )

    class Meta:
        model = SupportContract
        fields = ('name', 'vendor', 'contract_id', 'status', 'description',
                  'renewal_date', 'predecessors', 'tags')
        widgets = {
            'renewal_date': forms.DateInput(attrs={'type': 'date'}),
        }


class SupportContractFilterForm(NetBoxModelFilterSetForm):
    model = SupportContract
    status = forms.MultipleChoiceField(choices=ContractStatusChoices, required=False)
    vendor_id = DynamicModelMultipleChoiceField(
        queryset=Manufacturer.objects.all(),
        required=False,
        label='Vendor',
    )


class CoverageLineForm(LineQuantityFormMixin, AssignedObjectFormMixin, NetBoxModelForm):
    support_contract = DynamicModelChoiceField(queryset=SupportContract.objects.all())
    quantity = _quantity_field()
    device = _device_field()
    module = _module_field()
    funding_line_item = DynamicModelChoiceField(
        queryset=LineItem.objects.filter(line_type=LineItemTypeChoices.TYPE_SUPPORT),
        required=False,
        query_params={'line_type': LineItemTypeChoices.TYPE_SUPPORT},
        help_text='The support line item that paid for this coverage.',
    )
    service_level = DynamicModelChoiceField(
        queryset=ServiceLevel.objects.all(),
        required=False,
        help_text='Leave blank to use the funding line item\'s service level.',
    )
    start_date = _date_field('Leave blank to use the funding line item\'s start date.')
    end_date = _date_field('Leave blank to use the funding line item\'s end date.')
    price = _price_field('Leave blank to use the funding line item\'s unit price.')

    fieldsets = (
        FieldSet('support_contract', 'funding_line_item', name='Contract'),
        FieldSet('quantity', 'device', 'module', name='Covered Object (leave both blank if pending)'),
        FieldSet('service_level', 'start_date', 'end_date', 'price', name='Coverage'),
        FieldSet('tags', name='Tags'),
    )

    class Meta:
        model = CoverageLine
        fields = ('support_contract', 'funding_line_item', 'service_level',
                  'start_date', 'end_date', 'price', 'tags')


class CoverageLineBulkEditForm(NetBoxModelBulkEditForm):
    model = CoverageLine
    funding_line_item = DynamicModelChoiceField(
        queryset=LineItem.objects.filter(line_type=LineItemTypeChoices.TYPE_SUPPORT),
        required=False,
        query_params={'line_type': LineItemTypeChoices.TYPE_SUPPORT},
    )
    service_level = DynamicModelChoiceField(queryset=ServiceLevel.objects.all(), required=False)
    start_date = _date_field()
    end_date = _date_field()
    price = _price_field()

    fieldsets = (
        FieldSet('funding_line_item', 'service_level', 'start_date', 'end_date', 'price'),
    )
    nullable_fields = ('funding_line_item',)


class CoverageLineFilterForm(NetBoxModelFilterSetForm):
    model = CoverageLine
    support_contract_id = DynamicModelMultipleChoiceField(
        queryset=SupportContract.objects.all(),
        required=False,
        label='Support contract',
    )
    status = forms.MultipleChoiceField(choices=CoverageStatusChoices, required=False)
    service_level_id = DynamicModelMultipleChoiceField(
        queryset=ServiceLevel.objects.all(),
        required=False,
        label='Service level',
    )


# ---------------------------------------------------------------------------
# Licenses
# ---------------------------------------------------------------------------

class LicenseForm(ContractFormMixin, NetBoxModelForm):
    vendor = DynamicModelChoiceField(queryset=Manufacturer.objects.all())
    predecessors = DynamicModelMultipleChoiceField(
        queryset=License.objects.all(),
        required=False,
        label='Replaces',
        help_text=REPLACES_HELP,
    )

    fieldsets = (
        FieldSet('name', 'vendor', 'license_number', 'status', 'description', name='License'),
        FieldSet('renewal_date', 'predecessors', name='Renewal'),
        FieldSet('tags', name='Tags'),
    )

    class Meta:
        model = License
        fields = ('name', 'vendor', 'license_number', 'status', 'description',
                  'renewal_date', 'predecessors', 'tags')
        widgets = {
            'renewal_date': forms.DateInput(attrs={'type': 'date'}),
        }


class LicenseFilterForm(NetBoxModelFilterSetForm):
    model = License
    status = forms.MultipleChoiceField(choices=ContractStatusChoices, required=False)
    vendor_id = DynamicModelMultipleChoiceField(
        queryset=Manufacturer.objects.all(),
        required=False,
        label='Vendor',
    )


class LicenseLineForm(LineQuantityFormMixin, AssignedObjectFormMixin, NetBoxModelForm):
    license = DynamicModelChoiceField(queryset=License.objects.all())
    quantity = _quantity_field()
    device = _device_field()
    module = _module_field()
    funding_line_item = DynamicModelChoiceField(
        queryset=LineItem.objects.filter(line_type=LineItemTypeChoices.TYPE_LICENSE),
        required=False,
        query_params={'line_type': LineItemTypeChoices.TYPE_LICENSE},
        help_text='The license line item that paid for this license.',
    )
    license_type = DynamicModelChoiceField(
        queryset=LicenseType.objects.all(),
        required=False,
        help_text='Leave blank to use the funding line item\'s license type.',
    )
    start_date = _date_field('Leave blank to use the funding line item\'s start date.')
    end_date = _date_field('Subscriptions only. Leave blank to use the funding line item\'s end date.')
    price = _price_field('Leave blank to use the funding line item\'s unit price.')

    fieldsets = (
        FieldSet('license', 'funding_line_item', name='License'),
        FieldSet('quantity', 'device', 'module', name='Licensed Object (leave both blank if pending)'),
        FieldSet('license_type', 'billing_term', 'start_date', 'end_date', 'price', name='Term'),
        FieldSet('license_key', name='Activation'),
        FieldSet('tags', name='Tags'),
    )

    class Meta:
        model = LicenseLine
        fields = ('license', 'funding_line_item', 'license_type', 'billing_term',
                  'start_date', 'end_date', 'price', 'license_key', 'tags')


class LicenseLineBulkEditForm(NetBoxModelBulkEditForm):
    model = LicenseLine
    funding_line_item = DynamicModelChoiceField(
        queryset=LineItem.objects.filter(line_type=LineItemTypeChoices.TYPE_LICENSE),
        required=False,
        query_params={'line_type': LineItemTypeChoices.TYPE_LICENSE},
    )
    license_type = DynamicModelChoiceField(queryset=LicenseType.objects.all(), required=False)
    billing_term = forms.ChoiceField(choices=add_blank_choice(BillingTermChoices), required=False)
    start_date = _date_field()
    end_date = _date_field()
    price = _price_field()

    fieldsets = (
        FieldSet('funding_line_item', 'license_type', 'billing_term', 'start_date', 'end_date', 'price'),
    )
    nullable_fields = ('funding_line_item', 'end_date')


class LicenseLineFilterForm(NetBoxModelFilterSetForm):
    model = LicenseLine
    license_id = DynamicModelMultipleChoiceField(
        queryset=License.objects.all(),
        required=False,
        label='License',
    )
    status = forms.MultipleChoiceField(choices=CoverageStatusChoices, required=False)
    billing_term = forms.MultipleChoiceField(choices=BillingTermChoices, required=False)
    license_type_id = DynamicModelMultipleChoiceField(
        queryset=LicenseType.objects.all(),
        required=False,
        label='License type',
    )


# ---------------------------------------------------------------------------
# "Add to Support Contract" / "Add to License" (from a line item)
# ---------------------------------------------------------------------------

class AddToContractForm(forms.Form):
    """Creates lines on a new or existing contract/License, funded by one line item."""
    MODE_NEW = 'new'
    MODE_EXISTING = 'existing'
    SEED_PENDING = 'pending'
    SEED_QPI = 'qpi'
    SEED_CONTRACT = 'contract'

    contract_model = SupportContract
    noun = 'contract'

    mode = forms.ChoiceField(widget=forms.RadioSelect)
    existing_contract = DynamicModelChoiceField(
        queryset=SupportContract.objects.all(),
        required=False,
        help_text='Co-term additions, and renewals that keep the same number.',
    )
    name = forms.CharField(max_length=200, required=False)
    reference = forms.CharField(max_length=200, required=False)
    vendor = DynamicModelChoiceField(queryset=Manufacturer.objects.all(), required=False)
    predecessors = DynamicModelMultipleChoiceField(
        queryset=SupportContract.objects.all(),
        required=False,
        label='Replaces',
        help_text=REPLACES_HELP,
    )
    seed = forms.ChoiceField(widget=forms.RadioSelect, label='Cover')
    source_line_items = forms.ModelMultipleChoiceField(
        queryset=LineItem.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='From hardware line items',
    )
    source_contract = DynamicModelChoiceField(
        queryset=SupportContract.objects.all(),
        required=False,
    )
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    price = forms.DecimalField(max_digits=12, decimal_places=2, label='Price per line')

    def __init__(self, *args, line_item, **kwargs):
        super().__init__(*args, **kwargs)
        noun, model = self.noun, self.contract_model
        f = self.fields
        f['mode'].choices = ((self.MODE_NEW, f'New {noun}'), (self.MODE_EXISTING, f'Existing {noun}'))
        f['mode'].label = noun.capitalize()
        f['existing_contract'].label = f'Existing {noun}'
        f['reference'].label = model._meta.get_field(model.reference_attr).verbose_name.capitalize()
        for name in ('existing_contract', 'predecessors', 'source_contract'):
            f[name].queryset = model.objects.all()
        f['seed'].choices = (
            (self.SEED_PENDING, 'Blank pending lines (assign devices later)'),
            (self.SEED_QPI, 'Devices and modules from hardware line items on this QPI'),
            (self.SEED_CONTRACT, f'Devices and modules currently on a {noun} (renewal)'),
        )
        f['source_contract'].label = f'Copy from {noun}'
        f['source_contract'].help_text = (
            f'Leave blank to use the existing {noun} chosen above, or the {noun} this one replaces.'
        )
        hardware = LineItem.objects.filter(
            qpi=line_item.qpi, line_type=LineItemTypeChoices.TYPE_HARDWARE,
        ).filter(Q(device_type__isnull=False) | Q(module_type__isnull=False)).annotate(
            provisioned=Count('provisioned_items'),
        ).order_by('pk')
        f['source_line_items'].queryset = hardware
        f['source_line_items'].label_from_instance = (
            lambda li: f'{li.name or li.device_type or li.module_type} — {li.provisioned} provisioned'
        )
        if not self.is_bound and hardware.count() == 1:
            self.initial['source_line_items'] = [hardware.first().pk]

    def clean(self):
        cd = super().clean()
        if cd.get('mode') == self.MODE_EXISTING:
            if not cd.get('existing_contract'):
                self.add_error('existing_contract', f'Choose a {self.noun}.')
        elif cd.get('mode') == self.MODE_NEW:
            if not cd.get('name'):
                self.add_error('name', f'Required for a new {self.noun}.')
            if not cd.get('vendor'):
                self.add_error('vendor', f'Required for a new {self.noun}.')
        if cd.get('seed') == self.SEED_QPI and not cd.get('source_line_items'):
            self.add_error('source_line_items', 'Choose which hardware line items to pull devices from.')
        if cd.get('seed') == self.SEED_CONTRACT and not self.get_source_contract():
            self.add_error('source_contract', f'Choose a {self.noun} to copy devices from.')
        start, end = cd.get('start_date'), cd.get('end_date')
        if start and end and end < start:
            self.add_error('end_date', 'End date must be on or after the start date.')
        return cd

    def get_source_contract(self):
        cd = self.cleaned_data
        if cd.get('source_contract'):
            return cd['source_contract']
        if cd.get('mode') == self.MODE_EXISTING and cd.get('existing_contract'):
            return cd['existing_contract']
        predecessors = cd.get('predecessors')
        if predecessors:
            return predecessors.first()
        return None


class AddToSupportContractForm(AddToContractForm):
    contract_model = SupportContract
    noun = 'contract'


class AddToLicenseForm(AddToContractForm):
    contract_model = License
    noun = 'license'

    billing_term = forms.ChoiceField(choices=BillingTermChoices, widget=forms.RadioSelect)
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text='Subscriptions only.',
    )

    def clean(self):
        cd = super().clean()
        if cd.get('billing_term') == BillingTermChoices.TERM_PERPETUAL:
            cd['end_date'] = None
        elif not cd.get('end_date') and 'end_date' not in self.errors:
            self.add_error('end_date', 'Required for subscriptions.')
        return cd


# ---------------------------------------------------------------------------
# Lifecycle Records
# ---------------------------------------------------------------------------

class LifecycleRecordForm(NetBoxModelForm):
    device_types = DynamicModelMultipleChoiceField(
        queryset=DeviceType.objects.all(),
        required=False,
        label='Device types',
    )
    module_types = DynamicModelMultipleChoiceField(
        queryset=ModuleType.objects.all(),
        required=False,
        label='Module types',
    )

    fieldsets = (
        FieldSet('name', 'description', 'reference_url', 'notice_date', name='Lifecycle Record'),
        FieldSet('device_types', 'module_types', name='Applies To'),
        FieldSet('tags', name='Tags'),
    )

    class Meta:
        model = LifecycleRecord
        fields = ('name', 'description', 'device_types', 'module_types', 'reference_url', 'notice_date', 'tags')
        labels = {
            'reference_url': 'Reference URL',
            'notice_date': 'Notice date',
        }
        help_texts = {
            'reference_url': "Link to the vendor's end-of-life bulletin.",
            'notice_date': 'When the vendor announced it.',
        }
        widgets = {
            'notice_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        super().clean()
        cd = self.cleaned_data
        for error in LifecycleRecord.type_conflicts(
            device_types=list(cd.get('device_types') or []),
            module_types=list(cd.get('module_types') or []),
            exclude_pk=self.instance.pk,
        ):
            self.add_error(None, error)
        return cd


class LifecycleRecordFilterForm(NetBoxModelFilterSetForm):
    model = LifecycleRecord
    fieldsets = (
        FieldSet('q', 'filter_id', 'tag'),
        FieldSet('manufacturer_id', 'device_type_id', 'module_type_id', name='Applies To'),
    )
    manufacturer_id = DynamicModelMultipleChoiceField(
        queryset=Manufacturer.objects.all(),
        required=False,
        label='Vendor',
    )
    device_type_id = DynamicModelMultipleChoiceField(
        queryset=DeviceType.objects.all(),
        required=False,
        label='Device type',
    )
    module_type_id = DynamicModelMultipleChoiceField(
        queryset=ModuleType.objects.all(),
        required=False,
        label='Module type',
    )


class LifecycleMilestoneForm(forms.ModelForm):
    milestone_type = forms.ModelChoiceField(queryset=MilestoneType.objects.all(), label='Milestone')

    def __init__(self, *args, lifecycle_record, **kwargs):
        super().__init__(*args, **kwargs)
        self.lifecycle_record = lifecycle_record

    class Meta:
        model = LifecycleMilestone
        fields = ('milestone_type', 'date')
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_milestone_type(self):
        value = self.cleaned_data['milestone_type']
        dupes = self.lifecycle_record.milestones.filter(milestone_type=value).exclude(pk=self.instance.pk)
        if dupes.exists():
            raise forms.ValidationError(f'This record already has an "{value}" date. Edit that one instead.')
        return value


# ---------------------------------------------------------------------------
# Milestone Types
# ---------------------------------------------------------------------------

class MilestoneTypeForm(NetBoxModelForm):
    slug = SlugField()

    fieldsets = (
        FieldSet('name', 'slug', 'color', 'weight', 'description', name='EOx Milestone'),
        FieldSet('tags', name='Tags'),
    )

    class Meta:
        model = MilestoneType
        fields = ('name', 'slug', 'color', 'weight', 'description', 'tags')


class MilestoneTypeFilterForm(NetBoxModelFilterSetForm):
    model = MilestoneType


# ---------------------------------------------------------------------------
# Attachments
# ---------------------------------------------------------------------------

class AttachmentForm(forms.ModelForm):
    document_type = forms.ChoiceField(choices=[])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from netbox.plugins import get_plugin_config
        doc_types = get_plugin_config('netbox_tco', 'document_types')
        self.fields['document_type'].choices = [(t, t) for t in doc_types]
        if self.instance and self.instance.pk:
            self.fields['file'].required = False

    class Meta:
        model = Attachment
        fields = ('name', 'description', 'document_type', 'file')


