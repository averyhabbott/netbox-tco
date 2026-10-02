# netbox-tco

A NetBox plugin for tracking what your network gear really costs. It records hardware purchases, support contracts and licenses against the devices they pay for, so you can see a device's total cost of ownership right on its NetBox page.

> **Status: early alpha (0.0.1).** The purchasing, provisioning and support-contract features below are working. Licenses, EOS/EOL tracking and renewal notifications are still being built, and models may change between releases without upgrade paths.

## What it does

- **Tracks purchases from quote to invoice.** One record (a *QPI*: quote, purchase, invoice) follows a purchase through every stage, with its dates, owners, attachments, and line items for hardware, support and licenses.
- **Creates NetBox objects from what you bought.** A hardware line item opens NetBox's own Add Device, Add Module or Add Rack form with the type filled in, and links each new object back to the purchase that paid for it.
- **Tracks support contracts per device.** Each contract lists the devices and modules it covers, with dates and a price for each. Co-term additions and renewals add new lines to the same contract; a replacement contract takes over from the old one on its start date.
- **Adds devices to contracts in bulk**, straight from a support line item or from NetBox's Device and Module lists.
- **Shows cost on the Device page:** hardware price, annual recurring support, lifetime cost and cost per port. A **Support** tab lists every contract a device or module has been on.
- **Manages your vocabulary:** service levels and license types, each with the vendor part numbers that map to them.
- **Full REST API** for all plugin objects.

## Requirements

- NetBox 4.5.7 through 4.7
- Python 3.12 or later

## Quick start

```bash
pip install netbox-tco
```

Add `'netbox_tco'` to `PLUGINS` in NetBox's `configuration.py`, then run `python manage.py migrate` and restart NetBox and its RQ workers. The plugin appears under **TCO** in the navigation menu.

## Configuration

All settings are optional. Override them in `configuration.py`:

```python
PLUGINS_CONFIG = {
    'netbox_tco': {
        'hardware_price_sum': True,
        'renewal_thresholds': {'approaching': 90, 'due': 30},
    },
}
```

| Setting | Default | What it does |
| --- | --- | --- |
| `hardware_price_sum` | `True` | Include the cost of a device's installed modules (hardware and support) in the device's cost. |
| `port_interface_types` | Common copper and optical types | Interface types counted as ports for the per-port cost. |
| `renewal_thresholds` | `{'approaching': 90, 'due': 30}` | Days before a contract's renewal date that its renewal status changes. |
| `vendor_renewal_thresholds` | `{}` | Per-vendor overrides of `renewal_thresholds`, keyed by manufacturer slug. |
| `document_types` | Quote, PO, Invoice, Contract, License, Other | Choices for attachment types. |

## Recommended practices

- **RMA replacements:** change the serial number on the existing Device and add a journal entry. The device keeps its purchase price, support coverage, licenses and installed modules, so its cost history stays continuous.
- **Retiring hardware:** set the device's status (for example *Decommissioning* or *Offline*) instead of deleting it, so its lifetime cost can still be reported. If a covered device is deleted, its coverage lines are kept and marked *Retired*. NetBox only keeps change history for 90 days by default (`CHANGELOG_RETENTION`).

## License

Released under the GNU General Public License v3.0 (or later). See [LICENSE](https://github.com/averyhabbott/netbox-tco/blob/main/LICENSE).
