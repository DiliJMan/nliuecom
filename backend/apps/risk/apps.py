from django.apps import AppConfig


class RiskConfig(AppConfig):
    name = "apps.risk"
    label = "risk"

    def ready(self):
        from django.db.models.signals import post_migrate

        from apps.core import registry

        from .matrix import sync_builtin_matrix
        from .models import RiskAssessment, RiskMatrix, RiskScenario

        post_migrate.connect(sync_builtin_matrix, sender=self, dispatch_uid="sync_builtin_matrix")
        registry.register(
            registry.ObjectType(
                key="risk.riskmatrix",
                model=RiskMatrix,
                label="Risk matrix",
                domain_of=lambda obj: None,
            )
        )
        registry.register(
            registry.ObjectType(
                key="risk.riskassessment",
                model=RiskAssessment,
                label="Risk assessment",
                supports_custom_fields=True,
            )
        )
        registry.register(
            registry.ObjectType(
                key="risk.riskscenario",
                model=RiskScenario,
                label="Risk scenario",
                domain_of=lambda obj: obj.risk_assessment.domain,
                supports_custom_fields=True,
            )
        )
