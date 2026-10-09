"""Rules for objects that point at other objects (a scenario that names assets, and so on).

Every linked object must live in the same domain as the object, or in one of its ancestors,
and the person making the change must be allowed to view it. Without this, a link could pull
data across domain boundaries that the permission model keeps apart.
"""

from __future__ import annotations

from collections.abc import Iterable

from rest_framework import serializers

from apps.access import policy

from . import registry


def check_links(user, domain, links: dict[str, tuple[str, Iterable]]) -> None:
    """`links` maps a field name to (object type key, linked objects)."""
    allowed_domain_ids = {str(domain.pk), *domain.ancestor_ids()} if domain is not None else set()
    errors: dict[str, str] = {}
    for field, (type_key, objects) in links.items():
        info = registry.get(type_key)
        for obj in objects:
            if obj is None:
                continue
            target = info.domain_of(obj)
            if target is None:
                continue  # instance-wide object; visibility is checked by its own endpoint
            if str(target.pk) not in allowed_domain_ids:
                errors[field] = "Linked objects must be in the same domain or a parent domain."
                break
            if not policy.has_permission(user, f"{type_key}:view", target):
                errors[field] = "You cannot view one of the linked objects."
                break
    if errors:
        raise serializers.ValidationError(errors)
