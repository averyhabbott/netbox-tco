from django import forms
from django.db.models import Count, Q
from dcim.models import Device, DeviceType, Manufacturer, Module, ModuleType, RackType
from netbox.forms import NetBoxModelBulkEditForm, NetBoxModelForm, NetBoxModelFilterSetForm
from utilities.forms.fields import DynamicModelChoiceField, DynamicModelMultipleChoiceField, SlugField
from utilities.forms.rendering import FieldSet

from .choices import (
    BillingTermChoices, ContractStatusChoices, CoverageStatusChoices, LineItemTypeChoices,
    QPIStatusChoices,
)
from .models import (
    Attachment, CoverageLine, License, LicenseLine, LicensePartNumber, LicenseType,
    LifecycleMilestone, LifecycleRecord, LineItem, QPI, ServiceLevel,
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
# Support Contracts
# ---------------------------------------------------------------------------

class SupportContractForm(NetBoxModelForm):
    vendor = DynamicModelChoiceField(queryset=Manufacturer.objects.all())
    predecessors = DynamicModelMultipleChoiceField(
        queryset=SupportContract.objects.all(),
        required=False,
        label='Replaces',
        help_text='Only when the vendor issued a new contract number or contracts were merged.',
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

    def clean_predecessors(self):
        predecessors = self.cleaned_data['predecessors']
        if self.instance.pk and self.instance in predecessors:
            raise forms.ValidationError('A contract cannot replace itself.')
        return predecessors


class SupportContractFilterForm(NetBoxModelFilterSetForm):
    model = SupportContract
    status = forms.MultipleChoiceField(choices=ContractStatusChoices, required=False)
    vendor_id = DynamicModelMultipleChoiceField(
        queryset=Manufacturer.objects.all(),
        required=False,
        label='Vendor',
    )


class CoverageLineForm(NetBoxModelForm):
    support_contract = DynamicModelChoiceField(queryset=SupportContract.objects.all())
    device = DynamicModelChoiceField(
        queryset=Device.objects.all(),
        required=False,
        selector=True,
    )
    module = DynamicModelChoiceField(
        queryset=Module.objects.all(),
        required=False,
        selector=True,
    )
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
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text='Leave blank to use the funding line item\'s start date.',
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text='Leave blank to use the funding line item\'s end date.',
    )
    price = forms.DecimalField(
        required=False,
        max_digits=12,
        decimal_places=2,
        help_text='Leave blank to use the funding line item\'s unit price.',
    )

    fieldsets = (
        FieldSet('support_contract', 'funding_line_item', name='Contract'),
        FieldSet('device', 'module', name='Covered Object (leave both blank if pending)'),
        FieldSet('service_level', 'start_date', 'end_date', 'price', name='Coverage'),
        FieldSet('tags', name='Tags'),
    )

    class Meta:
        model = CoverageLine
        fields = ('support_contract', 'funding_line_item', 'service_level',
                  'start_date', 'end_date', 'price', 'tags')

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


class CoverageLineBulkEditForm(NetBoxModelBulkEditForm):
    model = CoverageLine
    funding_line_item = DynamicModelChoiceField(
        queryset=LineItem.objects.filter(line_type=LineItemTypeChoices.TYPE_SUPPORT),
        required=False,
        query_params={'line_type': LineItemTypeChoices.TYPE_SUPPORT},
    )
    service_level = DynamicModelChoiceField(queryset=ServiceLevel.objects.all(), required=False)
    start_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    price = forms.DecimalField(required=False, max_digits=12, decimal_places=2)

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


class AddToSupportContractForm(forms.Form):
    """Creates coverage lines on a new or existing contract from a support line item."""
    MODE_NEW = 'new'
    MODE_EXISTING = 'existing'
    SEED_PENDING = 'pending'
    SEED_QPI = 'qpi'
    SEED_CONTRACT = 'contract'

    mode = forms.ChoiceField(
        choices=((MODE_NEW, 'New contract'), (MODE_EXISTING, 'Existing contract')),
        widget=forms.RadioSelect,
        label='Contract',
    )
    existing_contract = DynamicModelChoiceField(
        queryset=SupportContract.objects.all(),
        required=False,
        label='Existing contract',
        help_text='Co-term additions, and renewals that keep the same contract number.',
    )
    name = forms.CharField(max_length=200, required=False)
    contract_id = forms.CharField(max_length=200, required=False, label='Contract ID')
    vendor = DynamicModelChoiceField(queryset=Manufacturer.objects.all(), required=False)
    predecessors = DynamicModelMultipleChoiceField(
        queryset=SupportContract.objects.all(),
        required=False,
        label='Replaces',
        help_text='Only when the vendor issued a new contract number or contracts were merged.',
    )
    seed = forms.ChoiceField(
        choices=(
            (SEED_PENDING, 'Blank pending lines (assign devices later)'),
            (SEED_QPI, 'Devices and modules provisioned on this QPI'),
            (SEED_CONTRACT, 'Devices and modules currently on a contract (renewal)'),
        ),
        widget=forms.RadioSelect,
        label='Cover',
    )
    source_contract = DynamicModelChoiceField(
        queryset=SupportContract.objects.all(),
        required=False,
        label='Copy from contract',
        help_text='Leave blank to use the existing contract chosen above, or the contract this one replaces.',
    )
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    price = forms.DecimalField(
        max_digits=12, decimal_places=2,
        label='Price per line',
    )

    fieldsets = (
        FieldSet('mode', 'existing_contract', name='Contract'),
        FieldSet('name', 'contract_id', 'vendor', 'predecessors', name='New Contract'),
        FieldSet('seed', 'source_contract', name='Coverage'),
        FieldSet('start_date', 'end_date', 'price', name='Term'),
    )

    def clean(self):
        cd = super().clean()
        if cd.get('mode') == self.MODE_EXISTING:
            if not cd.get('existing_contract'):
                self.add_error('existing_contract', 'Choose a contract.')
        elif cd.get('mode') == self.MODE_NEW:
            if not cd.get('name'):
                self.add_error('name', 'Required for a new contract.')
            if not cd.get('vendor'):
                self.add_error('vendor', 'Required for a new contract.')
        if cd.get('seed') == self.SEED_CONTRACT and not self.get_source_contract():
            self.add_error('source_contract', 'Choose a contract to copy devices from.')
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


class AssignCoverageForm(forms.Form):
    """Assigns selected devices/modules to a contract's pending coverage lines."""
    support_contract = forms.ModelChoiceField(
        queryset=SupportContract.objects.none(),
        label='Support contract',
        help_text='Only contracts with pending coverage lines are listed.',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        qs = SupportContract.objects.filter(
            coverage_lines__status=CoverageStatusChoices.STATUS_PENDING,
        ).annotate(
            pending=Count('coverage_lines', filter=Q(coverage_lines__status=CoverageStatusChoices.STATUS_PENDING)),
        ).distinct().order_by('name')
        self.fields['support_contract'].queryset = qs
        self.fields['support_contract'].label_from_instance = (
            lambda c: f'{c} — {c.pending} pending line{"s" if c.pending != 1 else ""}'
        )


# ---------------------------------------------------------------------------
# Licenses
# ---------------------------------------------------------------------------

class LicenseForm(NetBoxModelForm):
    vendor = DynamicModelChoiceField(queryset=Manufacturer.objects.all())
    funding_line_items = DynamicModelMultipleChoiceField(
        queryset=LineItem.objects.filter(line_type=LineItemTypeChoices.TYPE_LICENSE),
        required=False,
        label='Funding line items',
    )
    predecessors = DynamicModelMultipleChoiceField(
        queryset=License.objects.all(),
        required=False,
        label='Predecessors',
    )

    fieldsets = (
        FieldSet('vendor', 'status', name='General'),
        FieldSet('funding_line_items', 'predecessors', name='Details'),
        FieldSet('tags', name='Tags'),
    )

    class Meta:
        model = License
        fields = ('vendor', 'status', 'funding_line_items', 'predecessors', 'tags')


class LicenseFilterForm(NetBoxModelFilterSetForm):
    model = License
    status = forms.MultipleChoiceField(choices=ContractStatusChoices, required=False)
    vendor_id = DynamicModelMultipleChoiceField(
        queryset=Manufacturer.objects.all(),
        required=False,
        label='Vendor',
    )


class LicenseLineForm(forms.ModelForm):
    device = DynamicModelChoiceField(
        queryset=Device.objects.all(),
        required=False,
        label='Device (leave blank if pending)',
    )
    license_type = DynamicModelChoiceField(queryset=LicenseType.objects.all())

    class Meta:
        model = LicenseLine
        fields = ('device', 'license_type', 'billing_term', 'start_date', 'end_date',
                  'renewal_date', 'price', 'license_key')
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'renewal_date': forms.DateInput(attrs={'type': 'date'}),
        }


# ---------------------------------------------------------------------------
# Lifecycle Records
# ---------------------------------------------------------------------------

class LifecycleRecordForm(NetBoxModelForm):
    device_types = DynamicModelMultipleChoiceField(
        queryset=DeviceType.objects.all(),
        required=False,
        label='Device types',
    )

    fieldsets = (
        FieldSet('name', 'device_types', 'reference_url', 'notice_date', name='General'),
        FieldSet('tags', name='Tags'),
    )

    class Meta:
        model = LifecycleRecord
        fields = ('name', 'device_types', 'reference_url', 'notice_date', 'tags')
        widgets = {
            'notice_date': forms.DateInput(attrs={'type': 'date'}),
        }


class LifecycleRecordFilterForm(NetBoxModelFilterSetForm):
    model = LifecycleRecord
    device_type_id = DynamicModelMultipleChoiceField(
        queryset=DeviceType.objects.all(),
        required=False,
        label='Device type',
    )


class LifecycleMilestoneForm(forms.ModelForm):
    class Meta:
        model = LifecycleMilestone
        fields = ('milestone_type', 'date')
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }


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


