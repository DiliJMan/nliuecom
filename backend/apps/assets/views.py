from apps.core.api import ScopedModelViewSet

from .models import Asset
from .serializers import AssetSerializer


class AssetViewSet(ScopedModelViewSet):
    object_type = "assets.asset"
    queryset = Asset.objects.select_related("domain").prefetch_related("depends_on")
    serializer_class = AssetSerializer
    filter_fields = ("domain", "type", "owner")
    search_fields = ("name", "ref_id", "description")
    ordering_fields = ("name", "created_at", "type")
