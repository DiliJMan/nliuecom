from django.conf import settings
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny
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


@extend_schema(
    responses=inline_serializer(
        "About",
        {
            "name": serializers.CharField(),
            "licence": serializers.CharField(),
            "licence_url": serializers.CharField(),
            "source_url": serializers.CharField(),
        },
    )
)
class AboutView(APIView):
    """Licence and source location. Public, so the sign-in page can show them too."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            {
                "name": "nliuecom",
                "licence": "AGPL-3.0-or-later",
                "licence_url": "https://www.gnu.org/licenses/agpl-3.0.html",
                "source_url": settings.SOURCE_URL,
            }
        )
