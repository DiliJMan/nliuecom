"""Registry of object types that take part in permissions, auditing and custom fields.

Each app registers its models once, in its AppConfig.ready(). Other layers then look an object
type up by its key (for example "domains.domain") instead of importing the model directly.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

STANDARD_ACTIONS = ("view", "add", "change", "delete")


@dataclass(frozen=True)
class ObjectType:
    key: str
    model: type
    label: str
    actions: tuple[str, ...] = STANDARD_ACTIONS
    # Returns the Domain an instance belongs to. None means the instance sits outside any domain.
    domain_of: Callable[[Any], Any] = field(default=lambda obj: getattr(obj, "domain", None))
    supports_custom_fields: bool = False
    audited: bool = True
    # Field names left out of audit records (secrets, large blobs).
    audit_exclude: tuple[str, ...] = ()


_registry: dict[str, ObjectType] = {}


def register(object_type: ObjectType) -> ObjectType:
    existing = _registry.get(object_type.key)
    if existing is not None and existing.model is not object_type.model:
        raise ValueError(f"Object type {object_type.key!r} is already registered")
    _registry[object_type.key] = object_type
    return object_type


def get(key: str) -> ObjectType:
    try:
        return _registry[key]
    except KeyError:
        raise KeyError(f"Unknown object type {key!r}") from None


def find(key: str) -> ObjectType | None:
    return _registry.get(key)


def all_types() -> list[ObjectType]:
    return sorted(_registry.values(), key=lambda t: t.key)


def key_for_model(model: type) -> str | None:
    for object_type in _registry.values():
        if object_type.model is model:
            return object_type.key
    return None


def all_permission_codes() -> set[str]:
    return {f"{t.key}:{action}" for t in _registry.values() for action in t.actions}
