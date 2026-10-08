from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.core import registry

from .models import Attachment, sha256_of, validate_upload


class AttachmentSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True)

    class Meta:
        model = Attachment
        fields = [
            "id",
            "domain",
            "file",
            "original_name",
            "content_type",
            "size",
            "sha256",
            "description",
            "linked_object_type",
            "linked_object_id",
            "uploaded_by",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "original_name",
            "content_type",
            "size",
            "sha256",
            "uploaded_by",
            "created_at",
        ]

    def validate(self, attrs):
        linked_type = attrs.get("linked_object_type", "")
        linked_id = attrs.get("linked_object_id", "")
        if bool(linked_type) != bool(linked_id):
            raise serializers.ValidationError("Give both linked_object_type and linked_object_id.")
        if linked_type:
            object_type = registry.find(linked_type)
            if object_type is None or not object_type.model.objects.filter(pk=linked_id).exists():
                raise serializers.ValidationError("The linked object does not exist.")
        return attrs

    def create(self, validated_data):
        uploaded = validated_data["file"]
        try:
            name = validate_upload(uploaded)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"file": exc.messages}) from None
        return Attachment.objects.create(
            original_name=name,
            # The browser's claimed type is recorded for display only and never used to serve.
            content_type=(getattr(uploaded, "content_type", "") or "")[:150],
            size=uploaded.size,
            sha256=sha256_of(uploaded),
            uploaded_by=self.context["request"].user,
            **validated_data,
        )
