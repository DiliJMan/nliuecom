from rest_framework.decorators import action
from rest_framework.response import Response

from apps.access import policy
from apps.core.api import ScopedModelViewSet

from .models import Domain
from .serializers import DomainSerializer


class DomainViewSet(ScopedModelViewSet):
    object_type = "domains.domain"
    domain_lookup = "pk"
    queryset = Domain.objects.all()
    serializer_class = DomainSerializer
    filterset_fields = ["kind", "parent"]

    def perform_create(self, serializer):
        # Creating beneath a parent needs "add" there; a new top-level domain needs a superuser.
        self.require("add", serializer.validated_data.get("parent"))
        serializer.save()

    def perform_update(self, serializer):
        if "parent" in serializer.validated_data:
            new_parent = serializer.validated_data["parent"]
            if (new_parent.pk if new_parent else None) != serializer.instance.parent_id:
                self.require("add", new_parent)
        serializer.save()

    @action(detail=False, methods=["get"])
    def tree(self, request):
        """The domains the caller can see, nested. A visible domain whose parent is hidden
        becomes a top-level node in that caller's tree."""
        domains = list(self.get_queryset().order_by("path"))
        nodes = {
            str(d.pk): {
                "id": str(d.pk),
                "name": d.name,
                "kind": d.kind,
                "depth": d.depth,
                "children": [],
            }
            for d in domains
        }
        roots = []
        for d in domains:
            node = nodes[str(d.pk)]
            parent = nodes.get(str(d.parent_id)) if d.parent_id else None
            (parent["children"] if parent else roots).append(node)
        return Response(roots)

    @action(detail=True, methods=["get"])
    def effective_permissions(self, request, pk=None):
        domain = self.get_object()
        return Response(sorted(policy.effective_permissions(request.user, domain)))
