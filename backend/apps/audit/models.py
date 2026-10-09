import hashlib
import json

from django.db import models

GENESIS_HASH = "0" * 64


class AuditImmutableError(Exception):
    """Raised on any attempt to change or remove an audit record."""


class AuditQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise AuditImmutableError("Audit events cannot be updated")

    def delete(self):
        raise AuditImmutableError("Audit events cannot be deleted")

    def bulk_update(self, *args, **kwargs):
        raise AuditImmutableError("Audit events cannot be updated")


class AuditEvent(models.Model):
    """One entry in an append-only, hash-chained log.

    Each record stores the hash of its predecessor and a hash over its own content, so removing,
    reordering or editing any record breaks the chain from that point on. `verify_chain` finds
    the first break. A database trigger (see the migrations) also rejects UPDATE and DELETE.
    """

    class Action(models.TextChoices):
        CREATE = "create"
        UPDATE = "update"
        DELETE = "delete"
        LOGIN = "login"
        LOGOUT = "logout"
        LOGIN_FAILED = "login_failed"
        ACCESS = "access"
        OTHER = "other"

    timestamp = models.DateTimeField(db_index=True)
    actor_id = models.CharField(max_length=36, blank=True, db_index=True)
    actor_email = models.CharField(max_length=254, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    action = models.CharField(max_length=20, choices=Action.choices)
    object_type = models.CharField(max_length=100, blank=True, db_index=True)
    object_id = models.CharField(max_length=64, blank=True, db_index=True)
    object_repr = models.CharField(max_length=300, blank=True)
    domain_id = models.CharField(max_length=36, blank=True, db_index=True)
    changes = models.JSONField(default=dict, blank=True)
    prev_hash = models.CharField(max_length=64)
    hash = models.CharField(max_length=64, unique=True)

    objects = AuditQuerySet.as_manager()

    class Meta:
        ordering = ["-id"]
        indexes = [models.Index(fields=["object_type", "object_id", "-id"])]

    def __str__(self):
        return (
            f"{self.timestamp:%Y-%m-%d %H:%M:%S} {self.action} {self.object_type} {self.object_id}"
        )

    def content(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(timespec="microseconds"),
            "actor_id": self.actor_id,
            "actor_email": self.actor_email,
            "ip_address": self.ip_address,
            "action": self.action,
            "object_type": self.object_type,
            "object_id": self.object_id,
            "object_repr": self.object_repr,
            "domain_id": self.domain_id,
            "changes": self.changes,
        }

    def compute_hash(self) -> str:
        payload = json.dumps(
            {"prev": self.prev_hash, **self.content()},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise AuditImmutableError("Audit events cannot be modified")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise AuditImmutableError("Audit events cannot be deleted")
