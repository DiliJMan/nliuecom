from rest_framework.exceptions import ValidationError

from apps.core.api import ScopedModelViewSet

from .models import Role, RoleAssignment
from .serializers import RoleAssignmentSerializer, RoleSerializer


class RoleViewSet(ScopedModelViewSet):
    object_type = "access.role"
    domain_lookup = None
    queryset = Role.objects.all()
    serializer_class = RoleSerializer

    def perform_update(self, serializer):
        if serializer.instance.builtin:
            raise ValidationError("Built-in roles cannot be edited. Copy one to change it.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.builtin:
            raise ValidationError("Built-in roles cannot be deleted.")
        instance.delete()


class RoleAssignmentViewSet(ScopedModelViewSet):
    object_type = "access.roleassignment"
    queryset = RoleAssignment.objects.select_related("role", "domain", "user", "group")
    serializer_class = RoleAssignmentSerializer
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params
        for field in ("domain", "user", "group", "role"):
            if params.get(field):
                queryset = queryset.filter(**{field: params[field]})
        return queryset
