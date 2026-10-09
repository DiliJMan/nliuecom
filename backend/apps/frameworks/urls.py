from rest_framework.routers import DefaultRouter

from .views import FrameworkViewSet, RequirementMappingViewSet, RequirementNodeViewSet

router = DefaultRouter()
router.register("frameworks", FrameworkViewSet, basename="framework")
router.register("requirement-nodes", RequirementNodeViewSet, basename="requirementnode")
router.register("requirement-mappings", RequirementMappingViewSet, basename="requirementmapping")
urlpatterns = router.urls
