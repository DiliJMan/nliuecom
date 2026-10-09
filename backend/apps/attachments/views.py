from django.db import transaction
from django.http import FileResponse
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from apps.audit import service as audit
from apps.audit.models import AuditEvent
from apps.core.api import ScopedModelViewSet

from .models import Attachment
from .serializers import AttachmentSerializer


class AttachmentViewSet(ScopedModelViewSet):
    object_type = "attachments.attachment"
    queryset = Attachment.objects.all()
    serializer_class = AttachmentSerializer
    parser_classes = [MultiPartParser, FormParser]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    action_permissions = {"download": "view", "verify": "view"}

    def perform_destroy(self, instance):
        stored = instance.file
        with transaction.atomic():
            instance.delete()
            transaction.on_commit(lambda: stored.storage.delete(stored.name))

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        attachment = self.get_object()
        audit.record(
            AuditEvent.Action.ACCESS,
            object_type=self.object_type,
            object_id=attachment.pk,
            object_repr=attachment.original_name,
            domain_id=attachment.domain_id,
        )
        response = FileResponse(
            attachment.file.open("rb"),
            as_attachment=True,
            filename=attachment.original_name,
            content_type="application/octet-stream",
        )
        response["X-Content-Type-Options"] = "nosniff"
        response["Content-Security-Policy"] = "default-src 'none'; sandbox"
        return response

    @action(detail=True, methods=["post"])
    def verify(self, request, pk=None):
        attachment = self.get_object()
        return Response({"intact": attachment.verify_integrity(), "sha256": attachment.sha256})
