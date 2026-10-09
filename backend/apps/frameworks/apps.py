from django.apps import AppConfig


class FrameworksConfig(AppConfig):
    name = "apps.frameworks"
    label = "frameworks"

    def ready(self):
        from apps.core import registry

        from .models import Framework, RequirementMapping, RequirementNode

        registry.register(
            registry.ObjectType(
                key="frameworks.framework",
                model=Framework,
                label="Framework",
                domain_of=lambda obj: obj.domain,
            )
        )
        registry.register(
            registry.ObjectType(
                key="frameworks.requirementnode",
                model=RequirementNode,
                label="Framework requirement",
                domain_of=lambda obj: obj.framework.domain,
                # Imported frameworks can hold thousands of rows that never change.
                audited=False,
            )
        )
        registry.register(
            registry.ObjectType(
                key="frameworks.requirementmapping",
                model=RequirementMapping,
                label="Requirement mapping",
                actions=("view",),
                domain_of=lambda obj: None,
                audited=False,
            )
        )
