from rest_framework import serializers

from apps.attachments.models import Attachment
from apps.core.serializers import DomainObjectSerializer
from apps.frameworks.models import Framework, RequirementNode
from apps.frameworks.scope import framework_scope

from .models import AppliedControl, Evidence


class AppliedControlSerializer(DomainObjectSerializer):
    custom_fields_object_type = "controls.appliedcontrol"
    custom_fields = serializers.DictField(required=False)
    reference_node_ref = serializers.CharField(
        source="reference_node.ref_id", read_only=True, default=None
    )

    class Meta:
        model = AppliedControl
        fields = [
            "id",
            "domain",
            "name",
            "ref_id",
            "description",
            "status",
            "category",
            "priority",
            "effort",
            "control_impact",
            "eta",
            "expiry_date",
            "owner",
            "reference_node",
            "reference_node_ref",
            "link",
            "custom_fields",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_reference_node(self, node: RequirementNode | None):
        request = self.context.get("request")
        if node is not None and request is not None:
            visible = Framework.objects.filter(framework_scope(request.user), pk=node.framework_id)
            if not visible.exists():
                raise serializers.ValidationError("Requirement not found.")
        return node


class EvidenceSerializer(DomainObjectSerializer):
    custom_fields_object_type = "controls.evidence"
    link_fields = {
        "attachment": "attachments.attachment",
        "applied_controls": "controls.appliedcontrol",
    }
    custom_fields = serializers.DictField(required=False)
    attachment = serializers.PrimaryKeyRelatedField(
        queryset=Attachment.objects.all(), required=False, allow_null=True
    )
    applied_controls = serializers.PrimaryKeyRelatedField(
        many=True, queryset=AppliedControl.objects.all(), required=False
    )
    attachment_name = serializers.CharField(
        source="attachment.original_name", read_only=True, default=None
    )

    class Meta:
        model = Evidence
        fields = [
            "id",
            "domain",
            "name",
            "description",
            "attachment",
            "attachment_name",
            "url",
            "valid_until",
            "applied_controls",
            "custom_fields",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        has_file = "attachment" in attrs and attrs["attachment"] is not None
        if self.instance is None and not has_file and not attrs.get("url"):
            raise serializers.ValidationError("Give a file, a link, or both.")
        return attrs
