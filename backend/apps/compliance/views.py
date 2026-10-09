from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.core.api import ScopedModelViewSet

from . import service
from .models import ComplianceAssessment, RequirementAssessment
from .serializers import ComplianceAssessmentSerializer, RequirementAssessmentSerializer


class ComplianceAssessmentViewSet(ScopedModelViewSet):
    object_type = "compliance.complianceassessment"
    queryset = ComplianceAssessment.objects.select_related("domain", "framework")
    serializer_class = ComplianceAssessmentSerializer
    filter_fields = ("domain", "framework", "status", "owner")
    search_fields = ("name", "description")
    ordering_fields = ("name", "status", "due_date", "created_at")
    action_permissions = {"workbench": "view", "suggestions": "view"}

    def perform_create(self, serializer):
        self.require("add", self.creation_domain(serializer))
        assessment = serializer.save()
        service.populate(assessment)

    @extend_schema(responses=None)
    @action(detail=True, methods=["get"], pagination_class=None)
    def workbench(self, request, pk=None):
        """Every requirement of the framework, with this assessment's answer where one exists."""
        assessment = self.get_object()
        answers = {
            ra.requirement_id: ra
            for ra in assessment.requirement_assessments.prefetch_related(
                "applied_controls", "evidence"
            )
        }
        rows = []
        for node in assessment.framework.nodes.order_by("order"):
            ra = answers.get(node.pk)
            rows.append(
                {
                    "id": str(node.pk),
                    "ref_id": node.ref_id,
                    "name": node.name,
                    "description": node.description,
                    "parent": str(node.parent_id) if node.parent_id else None,
                    "assessable": node.assessable,
                    "weight": node.weight,
                    "assessment": None
                    if ra is None
                    else {
                        "id": str(ra.pk),
                        "result": ra.result,
                        "status": ra.status,
                        "observation": ra.observation,
                        "applied_controls": [str(c.pk) for c in ra.applied_controls.all()],
                        "evidence": [str(e.pk) for e in ra.evidence.all()],
                    },
                }
            )
        return Response(rows)

    @extend_schema(responses=None)
    @action(detail=True, methods=["get"], pagination_class=None)
    def suggestions(self, request, pk=None):
        """Results from another assessment that map onto requirements not yet assessed here."""
        assessment = self.get_object()
        source_id = request.query_params.get("source")
        source = self.get_queryset().filter(pk=source_id).first() if source_id else None
        if source is None:
            raise ValidationError({"source": "Give the id of another assessment you can view."})
        return Response(service.suggestions(assessment, source))


class RequirementAssessmentViewSet(ScopedModelViewSet):
    object_type = "compliance.requirementassessment"
    domain_lookup = "compliance_assessment__domain"
    queryset = RequirementAssessment.objects.select_related(
        "requirement", "compliance_assessment__domain"
    ).prefetch_related("applied_controls", "evidence")
    serializer_class = RequirementAssessmentSerializer
    http_method_names = ["get", "patch", "head", "options"]
    filter_fields = ("compliance_assessment", "result", "status")
    search_fields = ("requirement__ref_id", "requirement__name", "observation")
