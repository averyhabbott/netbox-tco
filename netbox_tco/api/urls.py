from netbox.api.routers import NetBoxRouter

from . import views

router = NetBoxRouter()
router.register('service-levels', views.ServiceLevelViewSet)
router.register('service-level-part-numbers', views.ServiceLevelPartNumberViewSet)
router.register('license-types', views.LicenseTypeViewSet)
router.register('license-part-numbers', views.LicensePartNumberViewSet)
router.register('qpis', views.QPIViewSet)
router.register('line-items', views.LineItemViewSet)
router.register('support-contracts', views.SupportContractViewSet)
router.register('coverage-lines', views.CoverageLineViewSet)
router.register('licenses', views.LicenseViewSet)
router.register('lifecycle-records', views.LifecycleRecordViewSet)

urlpatterns = router.urls
