import pytest
from django.db import connection

from apps.accounts.models import UserGroup
from apps.audit import service
from apps.audit.context import acting_as
from apps.audit.models import AuditEvent, AuditImmutableError
from apps.domains.models import Domain

pytestmark = pytest.mark.django_db


def test_create_update_delete_are_recorded_with_actor(admin):
    with acting_as(admin, ip="10.0.0.9"):
        domain = Domain.objects.create(name="Finance", kind="team")
        domain.description = "Money"
        domain.save()
        domain_id = domain.pk
        domain.delete()
    events = list(AuditEvent.objects.filter(object_id=str(domain_id)).order_by("id"))
    assert [e.action for e in events] == ["create", "update", "delete"]
    assert all(e.actor_email == admin.email and e.ip_address == "10.0.0.9" for e in events)
    assert events[1].changes == {"description": ["", "Money"]}
    assert events[0].domain_id == str(domain_id)


def test_unchanged_save_records_nothing(tree):
    before = AuditEvent.objects.count()
    tree["europe"].save()
    assert AuditEvent.objects.count() == before


def test_secrets_never_reach_the_log(make_user):
    user = make_user("secret@example.com")
    user.set_password("another-long-password-7")
    user.save()
    blob = " ".join(str(e.changes) for e in AuditEvent.objects.filter(object_type="accounts.user"))
    assert "password" not in blob and "pbkdf2" not in blob and "argon2" not in blob


def test_membership_changes_are_recorded(make_user):
    group = UserGroup.objects.create(name="SOC")
    user = make_user()
    group.members.add(user)
    event = AuditEvent.objects.filter(object_type="accounts.usergroup", action="update").first()
    assert event.changes == {"members": {"added": [str(user.pk)]}}


def test_chain_verifies_and_links_events(tree):
    intact, bad, checked = service.verify_chain()
    assert intact and bad is None and checked >= 5
    events = list(AuditEvent.objects.order_by("id"))
    assert events[0].prev_hash == "0" * 64
    assert all(b.prev_hash == a.hash for a, b in zip(events, events[1:], strict=False))


def test_orm_refuses_to_alter_or_delete_events(tree):
    event = AuditEvent.objects.first()
    event.object_repr = "changed"
    with pytest.raises(AuditImmutableError):
        event.save()
    with pytest.raises(AuditImmutableError):
        event.delete()
    with pytest.raises(AuditImmutableError):
        AuditEvent.objects.all().delete()
    with pytest.raises(AuditImmutableError):
        AuditEvent.objects.all().update(object_repr="x")


def test_database_trigger_blocks_raw_sql(tree):
    with connection.cursor() as cursor, pytest.raises(Exception, match="immutable"):
        cursor.execute("UPDATE audit_auditevent SET object_repr = 'x'")
    with connection.cursor() as cursor, pytest.raises(Exception, match="immutable"):
        cursor.execute("DELETE FROM audit_auditevent")


def test_tampering_is_detected_when_the_trigger_is_bypassed(tree):
    """Simulates an attacker with file access who drops the trigger and edits a record."""
    target = AuditEvent.objects.order_by("id")[2]
    with connection.cursor() as cursor:
        cursor.execute("DROP TRIGGER audit_auditevent_no_update")
        cursor.execute(
            "UPDATE audit_auditevent SET object_repr = 'forged' WHERE id = %s", [target.pk]
        )
    intact, bad, _ = service.verify_chain()
    assert not intact and bad == target.pk


def test_deleted_middle_record_breaks_the_chain(tree):
    victim = AuditEvent.objects.order_by("id")[1]
    with connection.cursor() as cursor:
        cursor.execute("DROP TRIGGER audit_auditevent_no_delete")
        cursor.execute("DELETE FROM audit_auditevent WHERE id = %s", [victim.pk])
    assert service.verify_chain()[0] is False


def test_global_log_is_scoped_by_domain(api, make_user, tree, grant, admin):
    auditor = make_user("aud@example.com")
    grant(auditor, "Auditor", tree["europe"])
    rows = api(auditor).get("/api/audit/").data["results"]
    assert rows and all(
        r["domain_id"] in {str(tree[k].pk) for k in ("europe", "france", "germany")} for r in rows
    )
    nobody = make_user("none@example.com")
    assert api(nobody).get("/api/audit/").data["results"] == []
    everything = api(admin).get("/api/audit/").data["count"]
    assert everything > len(rows)


def test_reader_cannot_open_the_global_log(api, make_user, tree, grant):
    reader = make_user()
    grant(reader, "Reader", tree["europe"])
    assert api(reader).get("/api/audit/").data["results"] == []


def test_object_trail_follows_view_permission(api, make_user, tree, grant):
    reader = make_user()
    grant(reader, "Reader", tree["europe"])
    ok = api(reader).get(f"/api/audit/trail/domains.domain/{tree['france'].pk}/")
    assert ok.status_code == 200 and ok.data[0]["action"] == "create"
    denied = api(reader).get(f"/api/audit/trail/domains.domain/{tree['asia'].pk}/")
    assert denied.status_code == 403
    assert api(reader).get("/api/audit/trail/nope.nope/1/").status_code == 404


def test_login_events_are_logged(make_user):
    from django.test import Client

    make_user("login@example.com", password="correct-horse-battery-1")
    client = Client()
    client.login(username="login@example.com", password="correct-horse-battery-1")
    client.login(username="login@example.com", password="wrong")
    actions = list(
        AuditEvent.objects.filter(object_type="accounts.user").values_list("action", flat=True)
    )
    assert "login" in actions and "login_failed" in actions


def test_forwarded_ip_is_only_trusted_when_enabled(settings):
    from django.test import RequestFactory

    from apps.audit.middleware import client_ip

    request = RequestFactory().get("/", HTTP_X_FORWARDED_FOR="203.0.113.7, 10.0.0.1")
    settings.TRUST_FORWARDED_FOR = False
    assert client_ip(request) == "127.0.0.1"
    settings.TRUST_FORWARDED_FOR = True
    assert client_ip(request) == "203.0.113.7"
    junk = RequestFactory().get("/", HTTP_X_FORWARDED_FOR="not-an-ip")
    assert client_ip(junk) == "127.0.0.1"
