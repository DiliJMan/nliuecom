from django.apps import AppConfig


class CustomFieldsConfig(AppConfig):
    name = "apps.customfields"
    label = "customfields"

    def ready(self):
        from apps.core import registry

        from .models import CustomFieldDefinition

        registry.register(
            registry.ObjectType(
                key="customfields.definition",
                model=CustomFieldDefinition,
                label="Custom field definition",
                domain_of=lambda obj: obj.domain,
            )
        )
