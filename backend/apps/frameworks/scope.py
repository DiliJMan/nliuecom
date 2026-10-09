from django.db.models import Q

from apps.access import policy

CODE = "frameworks.framework:view"


def framework_scope(user, prefix: str = "") -> Q:
    """Which frameworks a user can see: instance-wide ones (any role that can view frameworks)
    plus custom ones in domains where that role applies."""
    ids = policy.accessible_domain_ids(user, CODE)
    if ids is None:
        return Q()
    scope = Q(**{f"{prefix}domain__in": ids})
    if policy.has_any_grant(user, CODE):
        scope |= Q(**{f"{prefix}domain__isnull": True})
    return scope
