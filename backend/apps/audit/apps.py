from django.apps import AppConfig


class AuditConfig(AppConfig):
    name = "apps.audit"
    label = "audit"

    def ready(self):
        from apps.core import registry

        from . import signals  # noqa: F401
        from .models import AuditEvent

        registry.register(
            registry.ObjectType(
                key="audit.auditevent",
                model=AuditEvent,
                label="Audit event",
                actions=("view",),
                domain_of=lambda obj: None,
                audited=False,
            )
        )
