from netbox.plugins import PluginConfig
from .version import __version__


class NetBoxTCOConfig(PluginConfig):
    name = 'netbox_tco'
    verbose_name = 'NetBox TCO'
    description = 'Track hardware purchases, support contracts, licenses, and EOS/EOL with FinOps cost rollup'
    version = __version__
    author = 'Avery Abbott'
    author_email = 'averyhabbott@yahoo.com'
    base_url = 'tco'
    min_version = '4.5.7'
    max_version = '4.7.99'
    default_settings = {
        'document_types': ['Quote', 'PO', 'Invoice', 'Contract', 'License', 'Other'],
        'milestone_types': [
            'End of Sale',
            'End of SW Maintenance',
            'End of Security Support',
            'End of Support',
        ],
        'renewal_thresholds': {
            'approaching': 90,
            'due': 30,
        },
        'vendor_renewal_thresholds': {},
        'port_interface_types': [
            '1000base-t',
            '10gbase-t',
            '25gbase-x-sfp28',
            '40gbase-x-qsfpp',
            '100gbase-x-qsfp28',
            '400gbase-x-qsfpdd',
        ],
        'hardware_price_sum': True,
    }

    def ready(self):
        super().ready()
        from .signals import register_signals
        register_signals()
        from . import jobs  # noqa: F401 — registers the daily system job


config = NetBoxTCOConfig
