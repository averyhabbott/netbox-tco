from datetime import date

from django.db.models import Max

from netbox.jobs import JobRunner, system_job
from netbox.plugins import get_plugin_config

from .choices import RenewalStatusChoices

MINUTES_PER_DAY = 1440


@system_job(interval=MINUTES_PER_DAY)
class RenewalStatusJob(JobRunner):
    """
    Daily job: applies contract/License status transitions (Pending → Active, predecessors →
    Superseded), then computes each active record's renewal_status stage and saves it if changed.
    Licenses whose lines are all perpetual have no end date and stay OK.
    """

    class Meta:
        name = 'TCO Renewal Status Update'

    def run(self, *args, **kwargs):
        from .models import License, SupportContract
        from .choices import ContractStatusChoices

        thresholds = get_plugin_config('netbox_tco', 'renewal_thresholds')
        vendor_thresholds = get_plugin_config('netbox_tco', 'vendor_renewal_thresholds')
        today = date.today()

        for model in (SupportContract, License):
            for record in model.objects.filter(status__in=(
                ContractStatusChoices.STATUS_PENDING, ContractStatusChoices.STATUS_ACTIVE,
            )):
                record.apply_status_transitions(today)

            active = model.objects.filter(
                status=ContractStatusChoices.STATUS_ACTIVE
            ).select_related('vendor').annotate(latest_end=Max(f'{model.lines_attr}__end_date'))

            updated = 0
            for record in active:
                new_status = self._compute_status(
                    record.renewal_date or record.latest_end, today, thresholds,
                    vendor_thresholds, record.vendor.slug if record.vendor else None,
                )
                if record.renewal_status != new_status:
                    record.renewal_status = new_status
                    record.save(update_fields=['renewal_status'])
                    updated += 1

            self.logger.info(f'Updated renewal_status on {updated} {model._meta.verbose_name_plural}.')

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
