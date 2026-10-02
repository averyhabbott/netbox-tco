from datetime import date

from django.db.models import Max

from netbox.jobs import JobRunner, system_job
from netbox.plugins import get_plugin_config

from .choices import RenewalStatusChoices

MINUTES_PER_DAY = 1440


@system_job(interval=MINUTES_PER_DAY)
class RenewalStatusJob(JobRunner):
    """
    Daily job that evaluates SupportContracts and subscription LicenseLines,
    computes the correct renewal_status stage for each, and saves if changed.
    """

    class Meta:
        name = 'TCO Renewal Status Update'

    def run(self, *args, **kwargs):
        from .models import SupportContract, License
        from .choices import ContractStatusChoices

        thresholds = get_plugin_config('netbox_tco', 'renewal_thresholds')
        vendor_thresholds = get_plugin_config('netbox_tco', 'vendor_renewal_thresholds')
        today = date.today()

        # Support contracts: status transitions, then renewal stage from the effective renewal date
        for contract in SupportContract.objects.filter(status__in=(
            ContractStatusChoices.STATUS_PENDING, ContractStatusChoices.STATUS_ACTIVE,
        )):
            contract.apply_status_transitions(today)

        active_contracts = SupportContract.objects.filter(
            status=ContractStatusChoices.STATUS_ACTIVE
        ).select_related('vendor').annotate(latest_end=Max('coverage_lines__end_date'))

        updated = 0
        for contract in active_contracts:
            new_status = self._compute_status(
                contract.renewal_date or contract.latest_end, today, thresholds,
                vendor_thresholds, contract.vendor.slug if contract.vendor else None,
            )
            if contract.renewal_status != new_status:
                contract.renewal_status = new_status
                contract.save(update_fields=['renewal_status'])
                updated += 1

        self.logger.info(f'Updated renewal_status on {updated} support contract(s).')

        # Licenses (umbrella level — check any active subscription line)
        active_licenses = License.objects.filter(
            status=ContractStatusChoices.STATUS_ACTIVE
        ).prefetch_related('license_lines').select_related('vendor')

        updated = 0
        for license in active_licenses:
            subscription_lines = [
                ll for ll in license.license_lines.all()
                if ll.billing_term == 'subscription' and ll.renewal_date
            ]
            if not subscription_lines:
                continue

            # Use the soonest renewal date among its subscription lines
            soonest = min(ll.renewal_date for ll in subscription_lines)
            new_status = self._compute_status(
                soonest, today, thresholds,
                vendor_thresholds, license.vendor.slug if license.vendor else None,
            )
            if license.renewal_status != new_status:
                license.renewal_status = new_status
                license.save(update_fields=['renewal_status'])
                updated += 1

        self.logger.info(f'Updated renewal_status on {updated} license(s).')

    @staticmethod
    def _compute_status(renewal_date, today, global_thresholds, vendor_thresholds, vendor_slug):
        if renewal_date is None:
            return RenewalStatusChoices.STATUS_OK

        # Merge vendor override over global thresholds
        thresholds = dict(global_thresholds)
        if vendor_slug and vendor_slug in vendor_thresholds:
            thresholds.update(vendor_thresholds[vendor_slug])

        days_until = (renewal_date - today).days

        if days_until < 0:
            return RenewalStatusChoices.STATUS_EXPIRED
        if days_until <= thresholds.get('due', 30):
            return RenewalStatusChoices.STATUS_DUE
        if days_until <= thresholds.get('approaching', 90):
            return RenewalStatusChoices.STATUS_APPROACHING
        return RenewalStatusChoices.STATUS_OK
