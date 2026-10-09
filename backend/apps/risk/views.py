from django.db.models import Count
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.core.api import ScopedModelViewSet

from .models import RiskAssessment, RiskMatrix, RiskScenario
from .serializers import RiskAssessmentSerializer, RiskMatrixSerializer, RiskScenarioSerializer


class RiskMatrixViewSet(ScopedModelViewSet):
    object_type = "risk.riskmatrix"
    domain_lookup = None
    queryset = RiskMatrix.objects.all()
    serializer_class = RiskMatrixSerializer

    def perform_update(self, serializer):
        if serializer.instance.builtin:
            raise ValidationError("The built-in matrix cannot be edited. Create another one.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.builtin:
            raise ValidationError("The built-in matrix cannot be deleted.")
        instance.delete()


class RiskAssessmentViewSet(ScopedModelViewSet):
    object_type = "risk.riskassessment"
    queryset = RiskAssessment.objects.select_related("domain", "matrix")
    serializer_class = RiskAssessmentSerializer
    filter_fields = ("domain", "status", "owner")
    search_fields = ("name", "description")
    ordering_fields = ("name", "status", "due_date", "created_at")
    action_permissions = {"heatmap": "view"}

    def get_queryset(self):
        return super().get_queryset().annotate(scenario_count=Count("scenarios"))

    @extend_schema(responses=None)
    @action(detail=True, methods=["get"])
    def heatmap(self, request, pk=None):
        """How many scenarios sit in each matrix cell, for current and residual ratings."""
        assessment = self.get_object()
        matrix = assessment.matrix
        shape = [[0] * len(matrix.impact) for _ in matrix.probability]
        current, residual = [row[:] for row in shape], [row[:] for row in shape]
        unrated = 0
        for s in assessment.scenarios.all():
            if s.current_probability is None or s.current_impact is None:
                unrated += 1
            else:
                current[s.current_probability][s.current_impact] += 1
            if s.residual_probability is not None and s.residual_impact is not None:
                residual[s.residual_probability][s.residual_impact] += 1
        return Response(
            {
                "matrix": RiskMatrixSerializer(matrix).data,
                "current": current,
                "residual": residual,
                "unrated": unrated,
            }
        )


class RiskScenarioViewSet(ScopedModelViewSet):
    object_type = "risk.riskscenario"
    domain_lookup = "risk_assessment__domain"
    queryset = RiskScenario.objects.select_related(
        "risk_assessment__matrix", "risk_assessment__domain"
    ).prefetch_related("assets", "applied_controls")
    serializer_class = RiskScenarioSerializer
    filter_fields = ("risk_assessment", "treatment", "owner")
    search_fields = ("name", "ref_id", "description")
    ordering_fields = ("name", "ref_id", "created_at")

    def creation_domain(self, serializer):
        return serializer.validated_data["risk_assessment"].domain

    def perform_update(self, serializer):
        serializer.save()
