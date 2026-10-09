from rest_framework import serializers

from apps.customfields.serializers import CustomFieldsSerializerMixin

from .linking import check_links


class DomainObjectSerializer(CustomFieldsSerializerMixin, serializers.ModelSerializer):
    """Base for objects that live in a domain.

    Subclasses name the registry type their custom fields use, and list the relations to check
    in `link_fields` as {field name: registry key of the target}.
    """

    link_fields: dict[str, str] = {}

    def object_domain(self, attrs):
        return attrs.get("domain") or getattr(self.instance, "domain", None)

    def custom_fields_domain(self, attrs):
        return self.object_domain(attrs)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        request = self.context.get("request")
        domain = self.object_domain(attrs)
        if request is None or domain is None:
            return attrs
        links = {}
        for field, type_key in self.link_fields.items():
            if field in attrs:
                value = attrs[field]
                links[field] = (type_key, value if isinstance(value, list | tuple) else [value])
        if links:
            check_links(request.user, domain, links)
        return attrs
