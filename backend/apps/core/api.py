"""Shared building blocks for the REST API: scoped viewsets and error handling."""

from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import ProtectedError, Q
from rest_framework import permissions, status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from apps.access import policy

from . import registry

ACTION_FOR = {
    "list": "view",
    "retrieve": "view",
    "create": "add",
    "update": "change",
    "partial_update": "change",
    "destroy": "delete",
}


def exception_handler(exc, context):
    if isinstance(exc, ProtectedError):
        return Response(
            {"detail": "This object is still referenced by other records and cannot be deleted."},
            status=status.HTTP_409_CONFLICT,
        )
    if isinstance(exc, DjangoValidationError):
        detail = exc.message_dict if hasattr(exc, "error_dict") else {"detail": exc.messages}
        return Response(detail, status=status.HTTP_400_BAD_REQUEST)
    return drf_exception_handler(exc, context)


class ScopedPermission(permissions.BasePermission):
    """Object-level check against the policy layer. Collection-level scoping is in get_queryset."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        action = ACTION_FOR.get(view.action)
        if action is None:
            action = getattr(view, "action_permissions", {}).get(view.action, "change")
        return view.allowed(request.user, action, obj)


class ScopedModelViewSet(viewsets.ModelViewSet):
    """A model viewset whose rows and writes follow the user's domain-scoped roles.

    Subclasses set `object_type` (registry key) and may set `domain_lookup`, the ORM path from
    the model to its domain. Set it to None for objects that live outside any domain.
    """

    object_type: str = ""
    domain_lookup: str | None = "domain"
    permission_classes = [ScopedPermission]
    # Extra @action names mapped to the permission action they require.
    action_permissions: dict[str, str] = {}
    # Query-string conveniences. Only the names listed here are honoured.
    filter_fields: tuple[str, ...] = ()
    search_fields: tuple[str, ...] = ()
    ordering_fields: tuple[str, ...] = ()

    @property
    def type_info(self) -> registry.ObjectType:
        return registry.get(self.object_type)

    def code(self, action: str) -> str:
        return f"{self.object_type}:{action}"

    def allowed(self, user, action: str, obj) -> bool:
        domain = self.type_info.domain_of(obj)
        if domain is None:
            if action == "view":
                return policy.has_any_grant(user, self.code("view"))
            return user.is_superuser
        return policy.has_permission(user, self.code(action), domain)

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if self.domain_lookup is None:
            return queryset if policy.has_any_grant(user, self.code("view")) else queryset.none()
        return policy.scope_queryset(user, queryset, self.code("view"), self.domain_lookup)

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        params = self.request.query_params
        for name in self.filter_fields:
            value = params.get(name)
            if value not in (None, ""):
                queryset = queryset.filter(**{name: value})
        term = params.get("search", "").strip()
        if term and self.search_fields:
            match = Q()
            for name in self.search_fields:
                match |= Q(**{f"{name}__icontains": term})
            queryset = queryset.filter(match)
        ordering = params.get("ordering", "")
        if ordering.lstrip("-") in self.ordering_fields:
            queryset = queryset.order_by(ordering, "pk")
        return queryset

    def check_permissions(self, request):
        super().check_permissions(request)
        # Objects outside any domain have no scope to check later, so refuse creation up front.
        if self.action == "create" and self.domain_lookup is None and not request.user.is_superuser:
            raise PermissionDenied()

    def creation_domain(self, serializer):
        """The domain a new object will live in. Subclasses with another rule override this."""
        if self.domain_lookup in (None, "pk"):
            return None
        return serializer.validated_data.get(self.domain_lookup)

    def perform_create(self, serializer):
        self.require("add", self.creation_domain(serializer))
        serializer.save()

    def perform_update(self, serializer):
        # Moving an object into another domain counts as creating it there.
        new = serializer.validated_data.get("domain") if self.domain_lookup == "domain" else None
        if new is not None and new.pk != getattr(serializer.instance, "domain_id", None):
            self.require("add", new)
        serializer.save()

    def require(self, action: str, domain) -> None:
        """Raise unless the user may perform `action` in `domain` (None means outside domains)."""
        user = self.request.user
        ok = (
            user.is_superuser
            if domain is None
            else policy.has_permission(user, self.code(action), domain)
        )
        if not ok:
            raise PermissionDenied()
