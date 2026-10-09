from rest_framework import serializers

from .models import CustomFieldDefinition
from .service import CustomFieldError, validate_values


class CustomFieldsSerializerMixin:
    """Validates the `custom_fields` payload against the definitions that apply to the object.

    Subclasses implement `custom_fields_domain(attrs)`, returning the Domain the object will
    live in, so the right scoped definitions are used.
    """

    custom_fields_object_type: str = ""

    def custom_fields_domain(self, attrs):
        raise NotImplementedError

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if not self.custom_fields_object_type:
            return attrs
        if "custom_fields" in attrs or self.instance is None:
            try:
                attrs["custom_fields"] = validate_values(
                    self.custom_fields_object_type,
                    self.custom_fields_domain(attrs),
                    attrs.get("custom_fields"),
                )
            except CustomFieldError as exc:
                raise serializers.ValidationError({"custom_fields": exc.errors}) from None
        return attrs


class CustomFieldDefinitionSerializer(serializers.ModelSerializer):
    choices = serializers.ListField(child=serializers.CharField(), required=False)

    class Meta:
        model = CustomFieldDefinition
        fields = [
            "id",
            "object_type",
            "key",
            "label",
            "help_text",
            "field_type",
            "required",
            "choices",
            "domain",
            "order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
