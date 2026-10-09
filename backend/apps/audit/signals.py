"""Turns saves, deletes and sign-ins into audit events for every registered, audited type."""

from __future__ import annotations

import logging

from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.db.models.fields.files import FieldFile
from django.db.models.signals import m2m_changed, post_delete, post_save, pre_save
from django.dispatch import receiver

from apps.accounts import backends
from apps.core import registry

from . import context, service
from .middleware import client_ip
from .models import AuditEvent

log = logging.getLogger(__name__)
ALWAYS_SKIPPED = {"updated_at", "created_at"}


def _object_type(instance):
    key = registry.key_for_model(type(instance))
    object_type = registry.find(key) if key else None
    return object_type if object_type and object_type.audited else None


def snapshot(instance, object_type) -> dict:
    skipped = ALWAYS_SKIPPED | set(object_type.audit_exclude)
    data = {}
    for field in instance._meta.concrete_fields:
        if field.primary_key or field.name in skipped or field.attname in skipped:
            continue
        value = getattr(instance, field.attname)
        data[field.attname] = value.name if isinstance(value, FieldFile) else value
    return data


def _domain_id(instance, object_type) -> str:
    try:
        domain = object_type.domain_of(instance)
    except Exception:  # A broken getter must never block the write being audited.
        log.exception("domain lookup failed for %s", object_type.key)
        return ""
    return str(domain.pk) if domain is not None else ""


@receiver(pre_save)
def remember_previous_state(sender, instance, raw=False, **kwargs):
    object_type = _object_type(instance)
    if object_type is None or raw or instance._state.adding:
        return
    previous = sender._default_manager.filter(pk=instance.pk).first()
    instance._audit_previous = snapshot(previous, object_type) if previous else None


@receiver(post_save)
def record_save(sender, instance, created, raw=False, **kwargs):
    object_type = _object_type(instance)
    if object_type is None or raw:
        return
    current = snapshot(instance, object_type)
    if created:
        changes = {k: [None, v] for k, v in current.items() if v not in (None, "", [], {})}
        action = AuditEvent.Action.CREATE
    else:
        previous = getattr(instance, "_audit_previous", None) or {}
        changes = {k: [previous.get(k), v] for k, v in current.items() if previous.get(k) != v}
        if not changes:
            return
        action = AuditEvent.Action.UPDATE
    service.record(
        action,
        object_type=object_type.key,
        object_id=instance.pk,
        object_repr=str(instance),
        domain_id=_domain_id(instance, object_type),
        changes=changes,
    )


@receiver(post_delete)
def record_delete(sender, instance, **kwargs):
    object_type = _object_type(instance)
    if object_type is None:
        return
    current = snapshot(instance, object_type)
    service.record(
        AuditEvent.Action.DELETE,
        object_type=object_type.key,
        object_id=instance.pk,
        object_repr=str(instance),
        domain_id=_domain_id(instance, object_type),
        changes={k: [v, None] for k, v in current.items() if v not in (None, "", [], {})},
    )


@receiver(m2m_changed)
def record_membership(sender, instance, action, reverse, model, pk_set, **kwargs):
    if action not in {"post_add", "post_remove", "post_clear"} or reverse:
        return
    object_type = _object_type(instance)
    if object_type is None:
        return
    field = next(
        (f.name for f in instance._meta.many_to_many if f.remote_field.through is sender), "m2m"
    )
    verb = "added" if action == "post_add" else "removed"
    service.record(
        AuditEvent.Action.UPDATE,
        object_type=object_type.key,
        object_id=instance.pk,
        object_repr=str(instance),
        domain_id=_domain_id(instance, object_type),
        changes={field: {verb: sorted(str(p) for p in (pk_set or []))}},
    )


@receiver(user_logged_in)
def record_login(sender, request, user, **kwargs):
    backends.clear_failures(user.email)
    actor = context.Actor(user_id=str(user.pk), email=user.email, ip=_ip(request))
    service.record(
        AuditEvent.Action.LOGIN,
        object_type="accounts.user",
        object_id=user.pk,
        object_repr=user.email,
        actor=actor,
    )


@receiver(user_logged_out)
def record_logout(sender, request, user, **kwargs):
    if user is None:
        return
    actor = context.Actor(user_id=str(user.pk), email=user.email, ip=_ip(request))
    service.record(
        AuditEvent.Action.LOGOUT,
        object_type="accounts.user",
        object_id=user.pk,
        object_repr=user.email,
        actor=actor,
    )


@receiver(user_login_failed)
def record_failed_login(sender, credentials, request=None, **kwargs):
    email = str(credentials.get("username", ""))[:254]
    if email:
        backends.record_failure(email)
    service.record(
        AuditEvent.Action.LOGIN_FAILED,
        object_type="accounts.user",
        object_repr=email,
        actor=context.Actor(email=email, ip=_ip(request) if request else None),
        changes={"locked": backends.is_locked(email)} if email else {},
    )


def _ip(request):
    return client_ip(request)
