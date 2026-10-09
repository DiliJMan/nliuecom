from rest_framework import serializers

from apps.core.linking import check_links
from apps.core.serializers import DomainObjectSerializer
from apps.frameworks.models import Framework
from apps.frameworks.scope import framework_scope

from .models import ComplianceAssessment, RequirementAssessment


class ComplianceAssessmentSerializer(DomainObjectSerializer):
    custom_fields_object_type = "compliance.complianceassessment"
    custom_fields = serializers.DictField(required=False)
    framework_name = serializers.CharField(source="framework.name", read_only=True)
    summary = serializers.SerializerMethodField()

    class Meta:
        model = ComplianceAssessment
        fields = [
            "id",
            "domain",
            "name",
            "description",
            "framework",
            "framework_name",
            "status",
            "version",
            "eta",
            "due_date",
            "owner",
            "summary",
            "custom_fields",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_summary(self, assessment) -> dict:
        return assessment.summary()

    def validate_framework(self, value):
        if self.instance is not None and value != self.instance.framework:
            raise serializers.ValidationError(
                "The framework cannot change once the assessment exists."
            )
        request = self.context.get("request")
        if (
            request is not None
            and not Framework.objects.filter(framework_scope(request.user), pk=value.pk).exists()
        ):
            raise serializers.ValidationError("Framework not found.")
        return value


class RequirementAssessmentSerializer(serializers.ModelSerializer):
    ref_id = serializers.CharField(source="requirement.ref_id", read_only=True)
    name = serializers.CharField(source="requirement.name", read_only=True)
    description = serializers.CharField(source="requirement.description", read_only=True)

    class Meta:
        model = RequirementAssessment
        fields = [
            "id",
            "compliance_assessment",
            "requirement",
            "ref_id",
            "name",
            "description",
            "result",
            "status",
            "observation",
            "applied_controls",
            "evidence",
            "updated_at",
        ]
        read_only_fields = ["id", "compliance_assessment", "requirement", "updated_at"]

    def validate(self, attrs):
        request = self.context.get("request")
        domain = self.instance.compliance_assessment.domain if self.instance else None
        if request is not None and domain is not None:
            links = {}
            if "applied_controls" in attrs:
                links["applied_controls"] = ("controls.appliedcontrol", attrs["applied_controls"])
            if "evidence" in attrs:
                links["evidence"] = ("controls.evidence", attrs["evidence"])
            if links:
                check_links(request.user, domain, links)
        return attrs
