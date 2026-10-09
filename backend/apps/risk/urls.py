from rest_framework.routers import DefaultRouter

from .views import RiskAssessmentViewSet, RiskMatrixViewSet, RiskScenarioViewSet

router = DefaultRouter()
router.register("risk-matrices", RiskMatrixViewSet, basename="riskmatrix")
router.register("risk-assessments", RiskAssessmentViewSet, basename="riskassessment")
router.register("risk-scenarios", RiskScenarioViewSet, basename="riskscenario")
urlpatterns = router.urls
