from apps.core.api import ScopedModelViewSet
from apps.domains.models import Domain

from .models import CustomFieldDefinition
from .serializers import CustomFieldDefinitionSerializer
from .service import definitions_for


class CustomFieldDefinitionViewSet(ScopedModelViewSet):
    """Any signed-in user may read definitions (forms need them); writes follow domain roles."""

    object_type = "customfields.definition"
    queryset = CustomFieldDefinition.objects.select_related("domain")
    serializer_class = CustomFieldDefinitionSerializer

    def get_queryset(self):
        queryset = CustomFieldDefinition.objects.select_related("domain")
        if self.action in {"list", "retrieve"}:
            object_type = self.request.query_params.get("object_type")
            domain_id = self.request.query_params.get("domain")
            if object_type and domain_id:
                domain = Domain.objects.filter(pk=domain_id).first()
                ids = [d.pk for d in definitions_for(object_type, domain)] if domain else []
                return queryset.filter(pk__in=ids)
            if object_type:
                return queryset.filter(object_type=object_type)
            return queryset
        return super().get_queryset()

    def allowed(self, user, action, obj):
        if action == "view":
            return True
        return super().allowed(user, action, obj)

    def creation_domain(self, serializer):
        return serializer.validated_data.get("domain")  # None means a global definition

    def perform_update(self, serializer):
        if "domain" in serializer.validated_data:
            self.require("add", serializer.validated_data["domain"])
        serializer.save()
