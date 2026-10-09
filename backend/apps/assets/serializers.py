from rest_framework import serializers

from apps.core.serializers import DomainObjectSerializer

from .models import Asset


def creates_cycle(asset: Asset | None, dependencies) -> bool:
    """True if making `asset` depend on `dependencies` would close a loop."""
    if asset is None:
        return False
    seen: set = set()
    stack = list(dependencies)
    while stack:
        current = stack.pop()
        if current.pk == asset.pk:
            return True
        if current.pk in seen:
            continue
        seen.add(current.pk)
        stack.extend(current.depends_on.all())
    return False


class AssetSerializer(DomainObjectSerializer):
    custom_fields_object_type = "assets.asset"
    link_fields = {"depends_on": "assets.asset"}
    custom_fields = serializers.DictField(required=False)
    depends_on = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Asset.objects.all(), required=False
    )

    class Meta:
        model = Asset
        fields = [
            "id",
            "domain",
            "name",
            "ref_id",
            "description",
            "type",
            "depends_on",
            "owner",
            "business_value",
            "confidentiality",
            "integrity",
            "availability",
            "link",
            "custom_fields",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if creates_cycle(self.instance, attrs.get("depends_on", [])):
            raise serializers.ValidationError(
                {"depends_on": "Assets cannot depend on each other in a loop."}
            )
        return attrs
