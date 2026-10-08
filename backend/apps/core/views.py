from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from . import registry


@extend_schema(
    responses=inline_serializer(
        "ObjectType",
        {
            "key": serializers.CharField(),
            "label": serializers.CharField(),
            "actions": serializers.ListField(child=serializers.CharField()),
            "supports_custom_fields": serializers.BooleanField(),
        },
        many=True,
    )
)
class ObjectTypeListView(APIView):
    """Lists object types and their actions, so the role editor can offer every permission."""

    def get(self, request):
        return Response(
            [
                {
                    "key": t.key,
                    "label": t.label,
                    "actions": list(t.actions),
                    "supports_custom_fields": t.supports_custom_fields,
                }
                for t in registry.all_types()
            ]
        )
