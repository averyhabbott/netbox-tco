from utilities.choices import ChoiceSet


class QPIStatusChoices(ChoiceSet):
    key = 'QPI.status'

    STATUS_REQUESTED = 'requested'
    STATUS_RECEIVED = 'received'
    STATUS_SIGNED = 'signed'
    STATUS_RETURNED = 'returned'
    STATUS_SHIPPED = 'shipped'
    STATUS_COMPLETE = 'complete'
    STATUS_CANCELLED = 'cancelled'
    STATUS_LOST = 'lost'

    CHOICES = [
        (STATUS_REQUESTED, 'Quote Requested', 'cyan'),
        (STATUS_RECEIVED, 'Quote Received', 'blue'),
        (STATUS_SIGNED, 'Quote Signed', 'indigo'),
        (STATUS_RETURNED, 'Quote Returned', 'purple'),
        (STATUS_SHIPPED, 'Shipped', 'yellow'),
        (STATUS_COMPLETE, 'Complete', 'green'),
        (STATUS_CANCELLED, 'Cancelled', 'red'),
        (STATUS_LOST, 'Lost', 'gray'),
    ]


class LineItemTypeChoices(ChoiceSet):
    key = 'LineItem.line_type'

    TYPE_HARDWARE = 'hardware'
    TYPE_SUPPORT = 'support'
    TYPE_LICENSE = 'license'

    CHOICES = [
        (TYPE_HARDWARE, 'Hardware', 'blue'),
        (TYPE_SUPPORT, 'Support', 'green'),
        (TYPE_LICENSE, 'License', 'purple'),
    ]


class ContractStatusChoices(ChoiceSet):
    STATUS_PENDING = 'pending'
    STATUS_ACTIVE = 'active'
    STATUS_CANCELLED = 'cancelled'
    STATUS_SUPERSEDED = 'superseded'

    CHOICES = [
        (STATUS_PENDING, 'Pending', 'cyan'),
        (STATUS_ACTIVE, 'Active', 'green'),
        (STATUS_CANCELLED, 'Cancelled', 'gray'),
        (STATUS_SUPERSEDED, 'Superseded', 'yellow'),
    ]


class CoverageStatusChoices(ChoiceSet):
    """Status of a coverage line or license line."""
    STATUS_PENDING = 'pending'
    STATUS_ASSIGNED = 'assigned'
    STATUS_RETIRED = 'retired'

    CHOICES = [
        (STATUS_PENDING, 'Pending', 'cyan'),
        (STATUS_ASSIGNED, 'Assigned', 'green'),
        (STATUS_RETIRED, 'Retired', 'gray'),
    ]


class RenewalStatusChoices(ChoiceSet):
    STATUS_OK = 'ok'
    STATUS_APPROACHING = 'approaching'
    STATUS_DUE = 'due'
    STATUS_EXPIRED = 'expired'

    CHOICES = [
        (STATUS_OK, 'OK', 'green'),
        (STATUS_APPROACHING, 'Approaching', 'yellow'),
        (STATUS_DUE, 'Due', 'orange'),
        (STATUS_EXPIRED, 'Expired', 'red'),
    ]


class BillingTermChoices(ChoiceSet):
    key = 'LicenseLine.billing_term'

    TERM_PERPETUAL = 'perpetual'
    TERM_SUBSCRIPTION = 'subscription'

    CHOICES = [
        (TERM_PERPETUAL, 'Perpetual', 'blue'),
        (TERM_SUBSCRIPTION, 'Subscription', 'purple'),
    ]
