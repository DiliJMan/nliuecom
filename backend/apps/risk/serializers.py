from rest_framework import serializers

from apps.core.linking import check_links
from apps.core.serializers import DomainObjectSerializer

from .models import RiskAssessment, RiskMatrix, RiskScenario


class MatrixStepSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=60)
    description = serializers.CharField(max_length=300, required=False, allow_blank=True)


class MatrixLevelSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=60)
    colour = serializers.CharField(max_length=7)
    description = serializers.CharField(max_length=300, required=False, allow_blank=True)


class RiskMatrixSerializer(serializers.ModelSerializer):
    probability = MatrixStepSerializer(many=True)
    impact = MatrixStepSerializer(many=True)
    levels = MatrixLevelSerializer(many=True)
    grid = serializers.ListField(child=serializers.ListField(child=serializers.IntegerField()))

    class Meta:
        model = RiskMatrix
        fields = [
            "id",
            "name",
            "description",
            "probability",
            "impact",
            "levels",
            "grid",
            "builtin",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "builtin", "created_at", "updated_at"]


class RiskAssessmentSerializer(DomainObjectSerializer):
    custom_fields_object_type = "risk.riskassessment"
    custom_fields = serializers.DictField(required=False)
    scenario_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = RiskAssessment
        fields = [
            "id",
            "domain",
            "name",
            "description",
            "matrix",
            "status",
            "version",
            "eta",
            "due_date",
            "owner",
            "scenario_count",
            "custom_fields",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_matrix(self, value):
        if (
            self.instance is not None
            and value != self.instance.matrix
            and self.instance.scenarios.exists()
        ):
            raise serializers.ValidationError(
                "The matrix cannot change once scenarios have been rated."
            )
        return value


class LevelField(serializers.Field):
    def to_representation(self, value):
        return value


class RiskScenarioSerializer(serializers.ModelSerializer):
    # Custom fields use the assessment's domain, so this does not extend DomainObjectSerializer.
    custom_fields = serializers.DictField(required=False)
    current_level = serializers.SerializerMethodField()
    residual_level = serializers.SerializerMethodField()

    class Meta:
        model = RiskScenario
        fields = [
            "id",
            "risk_assessment",
            "ref_id",
            "name",
            "description",
            "threats",
            "vulnerabilities",
            "existing_controls",
            "assets",
            "applied_controls",
            "current_probability",
            "current_impact",
            "current_level",
            "residual_probability",
            "residual_impact",
            "residual_level",
            "treatment",
            "justification",
            "owner",
            "custom_fields",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_current_level(self, scenario) -> dict | None:
        return scenario.current_level()

    def get_residual_level(self, scenario) -> dict | None:
        return scenario.residual_level()

    def validate(self, attrs):
        from apps.customfields.service import CustomFieldError, validate_values

        assessment = attrs.get("risk_assessment") or (
            self.instance.risk_assessment if self.instance else None
        )
        if self.instance is not None and attrs.get("risk_assessment") not in (
            None,
            self.instance.risk_assessment,
        ):
            raise serializers.ValidationError(
                {"risk_assessment": "A scenario cannot move to another assessment."}
            )
        matrix = assessment.matrix
        for name, size in (
            ("current_probability", len(matrix.probability)),
            ("residual_probability", len(matrix.probability)),
            ("current_impact", len(matrix.impact)),
            ("residual_impact", len(matrix.impact)),
        ):
            value = attrs.get(name)
            if value is not None and not 0 <= value < size:
                raise serializers.ValidationError(
                    {name: f"Use a step from 0 to {size - 1} on this matrix."}
                )
        request = self.context.get("request")
        if request is not None:
            links = {}
            if "assets" in attrs:
                links["assets"] = ("assets.asset", attrs["assets"])
            if "applied_controls" in attrs:
                links["applied_controls"] = ("controls.appliedcontrol", attrs["applied_controls"])
            if links:
                check_links(request.user, assessment.domain, links)
        if "custom_fields" in attrs or self.instance is None:
            try:
                attrs["custom_fields"] = validate_values(
                    "risk.riskscenario", assessment.domain, attrs.get("custom_fields")
                )
            except CustomFieldError as exc:
                raise serializers.ValidationError({"custom_fields": exc.errors}) from None
        return attrs
