import re

from rest_framework import serializers

from .models import Framework, RequirementMapping, RequirementNode
from .scope import framework_scope


class FrameworkSerializer(serializers.ModelSerializer):
    node_count = serializers.IntegerField(read_only=True)
    assessable_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Framework
        fields = [
            "id",
            "slug",
            "name",
            "version",
            "provider",
            "description",
            "domain",
            "derived_from",
            "locked",
            "redistributable",
            "licence_note",
            "attribution",
            "source",
            "node_count",
            "assessable_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "derived_from",
            "locked",
            "redistributable",
            "licence_note",
            "attribution",
            "source",
            "created_at",
            "updated_at",
        ]

    def validate_domain(self, value):
        # A framework cannot change owner after creation: its assessments are scoped by it.
        if self.instance is not None and value != self.instance.domain:
            raise serializers.ValidationError("The owning domain cannot be changed.")
        return value


class DeriveSerializer(serializers.Serializer):
    domain = serializers.UUIDField()
    name = serializers.CharField(max_length=300)
    slug = serializers.SlugField(max_length=100, required=False)


class ImportSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=["scf", "iso27001", "project"])
    file = serializers.FileField(write_only=True)
    replace = serializers.BooleanField(required=False, default=False)
    domain = serializers.UUIDField(required=False, allow_null=True)


class RequirementNodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequirementNode
        fields = [
            "id",
            "framework",
            "ref_id",
            "name",
            "description",
            "parent",
            "order",
            "assessable",
            "weight",
            "extra",
        ]
        read_only_fields = ["id", "extra"]

    def validate_framework(self, value):
        if value.locked:
            raise serializers.ValidationError(
                "Imported frameworks are read-only. Derive a copy to customise it."
            )
        if self.instance is not None and value != self.instance.framework:
            raise serializers.ValidationError("A requirement cannot move to another framework.")
        request = self.context.get("request")
        if (
            request
            and not Framework.objects.filter(framework_scope(request.user), pk=value.pk).exists()
        ):
            raise serializers.ValidationError("Framework not found.")
        return value

    def validate(self, attrs):
        framework = attrs.get("framework") or (self.instance.framework if self.instance else None)
        if self.instance is not None and self.instance.framework.locked:
            raise serializers.ValidationError("Imported frameworks are read-only.")
        parent = attrs.get("parent")
        if parent is not None and parent.framework_id != framework.pk:
            raise serializers.ValidationError(
                {"parent": "The parent must be in the same framework."}
            )
        ref_id = attrs.get("ref_id", getattr(self.instance, "ref_id", None))
        clash = RequirementNode.objects.filter(framework=framework, ref_id=ref_id)
        if self.instance is not None:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError(
                {"ref_id": "This reference is already used in the framework."}
            )
        if parent is not None and self.instance is not None:
            node = parent
            while node is not None:
                if node.pk == self.instance.pk:
                    raise serializers.ValidationError(
                        {"parent": "A requirement cannot move beneath itself."}
                    )
                node = node.parent
        return attrs


class RequirementMappingSerializer(serializers.ModelSerializer):
    source_ref = serializers.CharField(source="source.ref_id", read_only=True)
    source_name = serializers.CharField(source="source.name", read_only=True)
    source_framework = serializers.CharField(source="source.framework.slug", read_only=True)
    target_ref = serializers.CharField(source="target.ref_id", read_only=True)
    target_name = serializers.CharField(source="target.name", read_only=True)
    target_framework = serializers.CharField(source="target.framework.slug", read_only=True)

    class Meta:
        model = RequirementMapping
        fields = [
            "id",
            "source",
            "source_ref",
            "source_name",
            "source_framework",
            "target",
            "target_ref",
            "target_name",
            "target_framework",
            "relationship",
            "origin",
        ]
        read_only_fields = fields


def slugify_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:100] or "framework"
