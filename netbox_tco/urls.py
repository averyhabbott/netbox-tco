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
    path('qpis/<int:qpi_pk>/attachments/add/',
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

    # Coverage Lines
    path('coverage-lines/', include(get_model_urls('netbox_tco', 'coverageline', detail=False))),
    path('coverage-lines/<int:pk>/', include(get_model_urls('netbox_tco', 'coverageline'))),
    path('line-items/<int:pk>/add-to-support-contract/',
         views.AddToSupportContractView.as_view(),
         name='lineitem_add_to_support_contract'),

    # Licenses
    path('licenses/', include(get_model_urls('netbox_tco', 'license', detail=False))),
    path('licenses/<int:pk>/', include(get_model_urls('netbox_tco', 'license'))),

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

    # Lifecycle Records
    path('lifecycle/', include(get_model_urls('netbox_tco', 'lifecyclerecord', detail=False))),
    path('lifecycle/<int:pk>/', include(get_model_urls('netbox_tco', 'lifecyclerecord'))),
]
