"""Built-in roles. They are rebuilt after every migration so new object types join them."""

from __future__ import annotations

from apps.core import registry

# Managed by instance administrators only; never part of a domain role.
ADMIN_ONLY = {"accounts.user", "accounts.usergroup", "access.role"}
# Visible to administrators and auditors, hidden from ordinary readers and contributors.
SENSITIVE = {"access.roleassignment", "audit.auditevent", "customfields.definition"}


def _codes(predicate) -> list[str]:
    return sorted(
        f"{t.key}:{action}"
        for t in registry.all_types()
        if t.key not in ADMIN_ONLY
        for action in t.actions
        if predicate(t.key, action)
    )


def definitions() -> dict[str, tuple[str, list[str]]]:
    ordinary = lambda key: key not in SENSITIVE  # noqa: E731
    return {
        "Reader": (
            "Read access to ordinary objects in the domain.",
            _codes(lambda k, a: ordinary(k) and a == "view"),
        ),
        "Contributor": (
            "Read, create and edit ordinary objects.",
            _codes(lambda k, a: ordinary(k) and a in {"view", "add", "change"}),
        ),
        "Manager": (
            "Full control of ordinary objects and a view of custom field definitions.",
            _codes(
                lambda k, a: (
                    (ordinary(k) and True) or (k == "customfields.definition" and a == "view")
                )
            ),
        ),
        "Auditor": (
            "Read-only view of everything in the domain, including the audit log.",
            _codes(lambda k, a: a == "view" and k != "access.roleassignment")
            + ["access.roleassignment:view"],
        ),
        "Domain administrator": (
            "Everything in the domain, including roles, custom fields and the audit log.",
            _codes(lambda k, a: True),
        ),
    }


def sync_builtin_roles(**kwargs):
    from .models import Role

    for name, (description, permissions) in definitions().items():
        Role.objects.update_or_create(
            name=name,
            defaults={"description": description, "permissions": permissions, "builtin": True},
        )
