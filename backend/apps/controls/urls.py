from rest_framework.routers import DefaultRouter

from .views import AppliedControlViewSet, EvidenceViewSet

router = DefaultRouter()
router.register("applied-controls", AppliedControlViewSet, basename="appliedcontrol")
router.register("evidence", EvidenceViewSet, basename="evidence")
urlpatterns = router.urls
