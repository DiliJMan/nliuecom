from __future__ import annotations

import json
from datetime import UTC, datetime

from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction

from . import context
from .models import GENESIS_HASH, AuditEvent


def _json_safe(value):
    return json.loads(json.dumps(value, cls=DjangoJSONEncoder))


@transaction.atomic
def record(
    action: str,
    *,
    object_type: str = "",
    object_id: str = "",
    object_repr: str = "",
    domain_id: str = "",
    changes: dict | None = None,
    actor: context.Actor | None = None,
) -> AuditEvent:
    """Append an event. The surrounding IMMEDIATE transaction keeps the chain linear."""
    actor = actor or context.current()
    last = AuditEvent.objects.order_by("-id").values_list("hash", flat=True).first()
    event = AuditEvent(
        timestamp=datetime.now(UTC),
        actor_id=actor.user_id or "",
        actor_email=actor.email,
        ip_address=actor.ip,
        action=action,
        object_type=object_type,
        object_id=str(object_id),
        object_repr=object_repr[:300],
        domain_id=str(domain_id or ""),
        changes=_json_safe(changes or {}),
        prev_hash=last or GENESIS_HASH,
    )
    event.hash = event.compute_hash()
    event.save()
    return event


def verify_chain() -> tuple[bool, int | None, int]:
    """Walk the whole chain. Returns (intact, id of first bad record or None, records checked)."""
    previous = GENESIS_HASH
    checked = 0
    for event in AuditEvent.objects.order_by("id").iterator(chunk_size=500):
        checked += 1
        if event.prev_hash != previous or event.hash != event.compute_hash():
            return False, event.pk, checked
        previous = event.hash
    return True, None, checked
