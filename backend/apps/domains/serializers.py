from rest_framework import serializers

from apps.customfields.serializers import CustomFieldsSerializerMixin

from .models import Domain


class DomainSerializer(CustomFieldsSerializerMixin, serializers.ModelSerializer):
    custom_fields_object_type = "domains.domain"
    custom_fields = serializers.DictField(required=False)

    class Meta:
        model = Domain
        fields = [
            "id",
            "name",
            "description",
            "kind",
            "parent",
            "path",
            "depth",
            "custom_fields",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "path", "depth", "created_at", "updated_at"]

    def custom_fields_domain(self, attrs):
        if self.instance is not None:
            return self.instance
        return attrs.get("parent")

    def validate(self, attrs):
        # Run the model rules (cycles, depth) so they surface as field errors, not a 500.
        from django.core.exceptions import ValidationError as DjangoValidationError

        attrs = super().validate(attrs)
        candidate = self.instance or Domain()
        parent = attrs.get("parent", candidate.parent if self.instance else None)
        if self.instance is not None:
            probe = Domain.objects.get(pk=self.instance.pk)
            probe.parent = parent
        else:
            probe = Domain(parent=parent)
        try:
            probe.clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from None
        return attrs
