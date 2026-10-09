from rest_framework.routers import DefaultRouter

from .views import ComplianceAssessmentViewSet, RequirementAssessmentViewSet

router = DefaultRouter()
router.register(
    "compliance-assessments", ComplianceAssessmentViewSet, basename="complianceassessment"
)
router.register(
    "requirement-assessments", RequirementAssessmentViewSet, basename="requirementassessment"
)
urlpatterns = router.urls
