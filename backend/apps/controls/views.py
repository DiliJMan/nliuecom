from apps.core.api import ScopedModelViewSet

from .models import AppliedControl, Evidence
from .serializers import AppliedControlSerializer, EvidenceSerializer


class AppliedControlViewSet(ScopedModelViewSet):
    object_type = "controls.appliedcontrol"
    queryset = AppliedControl.objects.select_related("domain", "reference_node")
    serializer_class = AppliedControlSerializer
    filter_fields = ("domain", "status", "category", "owner", "priority")
    search_fields = ("name", "ref_id", "description")
    ordering_fields = ("name", "status", "eta", "priority", "created_at")


class EvidenceViewSet(ScopedModelViewSet):
    object_type = "controls.evidence"
    queryset = Evidence.objects.select_related("domain", "attachment").prefetch_related(
        "applied_controls"
    )
    serializer_class = EvidenceSerializer
    filter_fields = ("domain", "applied_controls")
    search_fields = ("name", "description")
    ordering_fields = ("name", "valid_until", "created_at")
