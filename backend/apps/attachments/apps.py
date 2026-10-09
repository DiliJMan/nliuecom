from django.apps import AppConfig


class AttachmentsConfig(AppConfig):
    name = "apps.attachments"
    label = "attachments"

    def ready(self):
        from apps.core import registry

        from .models import Attachment

        registry.register(
            registry.ObjectType(key="attachments.attachment", model=Attachment, label="Attachment")
        )
