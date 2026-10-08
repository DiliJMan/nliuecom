"""The single place that decides whether a user may do something.

Rules:
* Instance administrators (`is_superuser`) may do anything.
* Otherwise a permission code applies to a domain when one of the user's role assignments, held
  directly or through a group, names that domain (or, when recursive, one of its ancestors) and
  the role contains the code.
* Anything without a domain (users, roles) needs a superuser, unless the code is granted
  somewhere, which allows read-only listing of such shared objects.
"""

from __future__ import annotations

from django.db.models import Q

from apps.domains.models import Domain

from .models import RoleAssignment


def _assignments_for(user):
    return RoleAssignment.objects.filter(Q(user=user) | Q(group__members=user)).select_related(
        "role", "domain"
    )


def granted_domains(user, code: str) -> list[RoleAssignment]:
    """Assignments of `user` whose role contains `code`."""
    if not user.is_authenticated or not user.is_active:
        return []
    return [a for a in _assignments_for(user).distinct() if code in a.role.permissions]


def accessible_domain_ids(user, code: str) -> set[str] | None:
    """Ids of domains where `code` applies. `None` means every domain (superuser)."""
    if not user.is_authenticated or not user.is_active:
        return set()
    if user.is_superuser:
        return None
    ids: set[str] = set()
    for assignment in granted_domains(user, code):
        if assignment.recursive:
            ids.update(
                str(pk)
                for pk in Domain.objects.filter(
                    path__startswith=assignment.domain.path
                ).values_list("pk", flat=True)
            )
        else:
            ids.add(str(assignment.domain_id))
    return ids


def has_permission(user, code: str, domain: Domain | None) -> bool:
    if not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser:
        return True
    if domain is None:
        return False
    for assignment in granted_domains(user, code):
        if assignment.domain_id == domain.pk:
            return True
        if assignment.recursive and domain.path.startswith(assignment.domain.path):
            return True
    return False


def has_any_grant(user, code: str) -> bool:
    return user.is_authenticated and (user.is_superuser or bool(granted_domains(user, code)))


def scope_queryset(user, queryset, code: str, domain_lookup: str = "domain"):
    """Restrict `queryset` to rows in domains where `user` holds `code`."""
    ids = accessible_domain_ids(user, code)
    if ids is None:
        return queryset
    return queryset.filter(**{f"{domain_lookup}__in": ids})


def effective_permissions(user, domain: Domain | None) -> set[str]:
    """Every permission code that applies to `user` at `domain`."""
    if not user.is_authenticated or not user.is_active:
        return set()
    from apps.core import registry

    if user.is_superuser:
        return registry.all_permission_codes()
    codes: set[str] = set()
    if domain is None:
        return codes
    for assignment in _assignments_for(user).distinct():
        if assignment.domain_id == domain.pk or (
            assignment.recursive and domain.path.startswith(assignment.domain.path)
        ):
            codes.update(assignment.role.permissions)
    return codes
