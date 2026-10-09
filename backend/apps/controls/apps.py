from django.apps import AppConfig


class ControlsConfig(AppConfig):
    name = "apps.controls"
    label = "controls"

    def ready(self):
        from apps.core import registry

        from .models import AppliedControl, Evidence

        registry.register(
            registry.ObjectType(
                key="controls.appliedcontrol",
                model=AppliedControl,
                label="Applied control",
                supports_custom_fields=True,
            )
        )
        registry.register(
            registry.ObjectType(
                key="controls.evidence",
                model=Evidence,
                label="Evidence",
                supports_custom_fields=True,
            )
        )
