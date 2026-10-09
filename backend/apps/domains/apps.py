from django.apps import AppConfig


class DomainsConfig(AppConfig):
    name = "apps.domains"
    label = "domains"

    def ready(self):
        from apps.core import registry

        from .models import Domain

        registry.register(
            registry.ObjectType(
                key="domains.domain",
                model=Domain,
                label="Domain",
                domain_of=lambda obj: obj,
                supports_custom_fields=True,
                audit_exclude=("path", "depth"),
            )
        )
