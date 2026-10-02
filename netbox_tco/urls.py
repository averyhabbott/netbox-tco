from django.urls import include, path
from utilities.urls import get_model_urls

from . import models, views

urlpatterns = [
    # Service Levels
    path('service-levels/', include(get_model_urls('netbox_tco', 'servicelevel', detail=False))),
    path('service-levels/<int:pk>/', include(get_model_urls('netbox_tco', 'servicelevel'))),

    # Service Level Part Numbers
    path('service-levels/<int:sl_pk>/part-numbers/add/',
         views.ServiceLevelPartNumberCreateView.as_view(),
         name='servicelevelpartnumber_add'),
    path('service-levels/part-numbers/<int:pk>/edit/',
         views.ServiceLevelPartNumberEditView.as_view(),
         name='servicelevelpartnumber_edit'),
    path('service-levels/part-numbers/<int:pk>/delete/',
         views.ServiceLevelPartNumberDeleteView.as_view(),
         name='servicelevelpartnumber_delete'),

    # License Types
    path('license-types/', include(get_model_urls('netbox_tco', 'licensetype', detail=False))),
    path('license-types/<int:pk>/', include(get_model_urls('netbox_tco', 'licensetype'))),

    # License Part Numbers
    path('license-types/<int:lt_pk>/part-numbers/add/',
         views.LicensePartNumberCreateView.as_view(),
         name='licensepartnumber_add'),
    path('license-types/part-numbers/<int:pk>/edit/',
         views.LicensePartNumberEditView.as_view(),
         name='licensepartnumber_edit'),
    path('license-types/part-numbers/<int:pk>/delete/',
         views.LicensePartNumberDeleteView.as_view(),
         name='licensepartnumber_delete'),

    # Attachments
    path('qpis/<int:parent_pk>/attachments/add/',
         views.AttachmentCreateView.as_view(),
         name='attachment_add'),
    path('attachments/<int:pk>/edit/',
         views.AttachmentEditView.as_view(),
         name='attachment_edit'),
    path('attachments/<int:pk>/delete/',
         views.AttachmentDeleteView.as_view(),
         name='attachment_delete'),

    # QPIs
    path('qpis/', include(get_model_urls('netbox_tco', 'qpi', detail=False))),
    path('qpis/<int:pk>/', include(get_model_urls('netbox_tco', 'qpi'))),

    # Line Items
    path('line-items/', include(get_model_urls('netbox_tco', 'lineitem', detail=False))),
    path('line-items/<int:pk>/', include(get_model_urls('netbox_tco', 'lineitem'))),

    # Provisioned Item bulk actions
    path('provisioned-items/remove/',
         views.ProvisionedItemBulkRemoveView.as_view(),
         name='provisioneditem_bulk_remove'),
    path('provisioned-items/delete/',
         views.ProvisionedItemBulkDeleteView.as_view(),
         name='provisioneditem_bulk_delete'),

    # Support Contracts
    path('support-contracts/', include(get_model_urls('netbox_tco', 'supportcontract', detail=False))),
    path('support-contracts/<int:pk>/', include(get_model_urls('netbox_tco', 'supportcontract'))),
    path('support-contracts/<int:parent_pk>/attachments/add/',
         views.SupportContractAttachmentCreateView.as_view(),
         name='supportcontract_attachment_add'),

    # Coverage Lines
    path('coverage-lines/', include(get_model_urls('netbox_tco', 'coverageline', detail=False))),
    path('coverage-lines/<int:pk>/', include(get_model_urls('netbox_tco', 'coverageline'))),
    path('line-items/<int:pk>/add-to-support-contract/',
         views.AddToSupportContractView.as_view(),
         name='lineitem_add_to_support_contract'),

    # Licenses
    path('licenses/', include(get_model_urls('netbox_tco', 'license', detail=False))),
    path('licenses/<int:pk>/', include(get_model_urls('netbox_tco', 'license'))),
    path('licenses/<int:parent_pk>/attachments/add/',
         views.LicenseAttachmentCreateView.as_view(),
         name='license_attachment_add'),

    # License Lines
    path('license-lines/', include(get_model_urls('netbox_tco', 'licenseline', detail=False))),
    path('license-lines/<int:pk>/', include(get_model_urls('netbox_tco', 'licenseline'))),
    path('line-items/<int:pk>/add-to-license/',
         views.AddToLicenseView.as_view(),
         name='lineitem_add_to_license'),

    # Attach TCO Item (core Device / Module list button)
    path('attach/<str:model_name>/',
         views.AttachTCOItemView.as_view(),
         name='attach_tco_item'),

    # EOx Milestones (MilestoneType)
    path('eox-milestones/', include(get_model_urls('netbox_tco', 'milestonetype', detail=False))),
    path('eox-milestones/<int:pk>/', include(get_model_urls('netbox_tco', 'milestonetype'))),

    # Lifecycle Records
    path('lifecycle/', include(get_model_urls('netbox_tco', 'lifecyclerecord', detail=False))),
    path('lifecycle/<int:pk>/', include(get_model_urls('netbox_tco', 'lifecyclerecord'))),
    path('lifecycle/<int:parent_pk>/attachments/add/',
         views.LifecycleRecordAttachmentCreateView.as_view(),
         name='lifecyclerecord_attachment_add'),

    # Lifecycle Milestones
    path('lifecycle/<int:record_pk>/milestones/add/',
         views.LifecycleMilestoneCreateView.as_view(),
         name='lifecyclemilestone_add'),
    path('lifecycle/milestones/<int:pk>/edit/',
         views.LifecycleMilestoneEditView.as_view(),
         name='lifecyclemilestone_edit'),
    path('lifecycle/milestones/<int:pk>/delete/',
         views.LifecycleMilestoneDeleteView.as_view(),
         name='lifecyclemilestone_delete'),
]
