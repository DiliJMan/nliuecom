from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access import policy
from apps.core import registry
from apps.core.api import ScopedPermission

from .models import AuditEvent
from .serializers import AuditEventSerializer

CODE = "audit.auditevent:view"


class AuditEventViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """The global log, limited to domains where the caller holds audit.auditevent:view.
    Events with no domain (sign-ins, user changes) are for instance administrators only."""

    serializer_class = AuditEventSerializer
    permission_classes = [ScopedPermission]
    queryset = AuditEvent.objects.all()

    def allowed(self, user, action, obj):
        if user.is_superuser:
            return True
        ids = policy.accessible_domain_ids(user, CODE) or set()
        return bool(obj.domain_id) and obj.domain_id in ids

    def get_queryset(self):
        queryset = AuditEvent.objects.all()
        ids = policy.accessible_domain_ids(self.request.user, CODE)
        if ids is not None:
            queryset = queryset.filter(domain_id__in=ids)
        params = self.request.query_params
        for field in ("object_type", "object_id", "action", "actor_id", "domain_id"):
            if params.get(field):
                queryset = queryset.filter(**{field: params[field]})
        if params.get("since"):
            queryset = queryset.filter(timestamp__gte=params["since"])
        if params.get("until"):
            queryset = queryset.filter(timestamp__lte=params["until"])
        return queryset


@extend_schema(responses=AuditEventSerializer(many=True))
class ObjectTrailView(APIView):
    """History of one object, available to anyone who may view that object itself."""

    def get(self, request, object_type, object_id):
        info = registry.find(object_type)
        if info is None:
            raise NotFound()
        obj = info.model.objects.filter(pk=object_id).first()
        if obj is None:
            raise NotFound()
        domain = info.domain_of(obj)
        if domain is None:
            allowed = request.user.is_superuser
        else:
            allowed = policy.has_permission(request.user, f"{object_type}:view", domain)
        if not allowed:
            raise PermissionDenied()
        events = AuditEvent.objects.filter(object_type=object_type, object_id=str(object_id))
        return Response(AuditEventSerializer(events[:500], many=True).data)
