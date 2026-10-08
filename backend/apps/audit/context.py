"""Who is acting right now. Set by middleware for requests and by `acting_as` elsewhere."""

from __future__ import annotations

import contextlib
from contextvars import ContextVar
from dataclasses import dataclass


@dataclass(frozen=True)
class Actor:
    user_id: str | None = None
    email: str = ""
    ip: str | None = None


_current: ContextVar[Actor] = ContextVar("audit_actor", default=Actor())  # noqa: B039  (frozen dataclass)


def current() -> Actor:
    return _current.get()


@contextlib.contextmanager
def acting_as(user=None, *, label: str = "", ip: str | None = None):
    """Attribute audit events to `user` (or to a named process such as "system:bootstrap")."""
    if user is not None and getattr(user, "is_authenticated", False):
        actor = Actor(user_id=str(user.pk), email=user.email, ip=ip)
    else:
        actor = Actor(email=label, ip=ip)
    token = _current.set(actor)
    try:
        yield actor
    finally:
        _current.reset(token)
