from django.apps import AppConfig


class AssetsConfig(AppConfig):
    name = "apps.assets"
    label = "assets"

    def ready(self):
        from apps.core import registry

        from .models import Asset

        registry.register(
            registry.ObjectType(
                key="assets.asset", model=Asset, label="Asset", supports_custom_fields=True
            )
        )
