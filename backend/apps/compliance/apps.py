from django.apps import AppConfig


class ComplianceConfig(AppConfig):
    name = "apps.compliance"
    label = "compliance"

    def ready(self):
        from apps.core import registry

        from .models import ComplianceAssessment, RequirementAssessment

        registry.register(
            registry.ObjectType(
                key="compliance.complianceassessment",
                model=ComplianceAssessment,
                label="Compliance assessment",
                supports_custom_fields=True,
            )
        )
        registry.register(
            registry.ObjectType(
                key="compliance.requirementassessment",
                model=RequirementAssessment,
                label="Requirement assessment",
                actions=("view", "change"),
                domain_of=lambda obj: obj.compliance_assessment.domain,
            )
        )
