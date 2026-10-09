from datetime import date, timedelta

import pytest
from django.core import mail
from django.core.management import call_command

from apps.tasks import service
from apps.tasks.models import Task

pytestmark = pytest.mark.django_db


def task(api, user, domain, **extra):
    return api(user).post(
        "/api/tasks/",
        {"domain": str(domain.pk), "title": "Review access list", **extra},
        format="json",
    )


def test_scoped_crud_and_validation(api, admin, make_user, tree, grant):
    contributor, outsider = make_user("c@example.com"), make_user("o@example.com")
    grant(contributor, "Contributor", tree["europe"])
    grant(outsider, "Reader", tree["asia"])
    created = task(api, contributor, tree["france"], priority=1, due_date="2026-12-01")
    assert created.status_code == 201, created.data
    assert api(outsider).get("/api/tasks/").data["count"] == 0
    assert task(api, contributor, tree["asia"]).status_code == 403
    for bad in (
        {"priority": 7},
        {"recurrence": "hourly"},
        {"reminder_days_before": 99},
        {"recurrence": "weekly"},
    ):
        assert task(api, admin, tree["france"], **bad).status_code == 400, bad


def test_assignee_filters_and_overdue_flag(api, admin, make_user, tree):
    me = make_user("me@example.com", is_superuser=True)
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    task(api, admin, tree["france"], title="Mine", assignee=str(me.pk), due_date=yesterday)
    task(api, admin, tree["france"], title="Nobody's")
    mine = api(me).get("/api/tasks/?assignee=me").data["results"]
    assert [t["title"] for t in mine] == ["Mine"] and mine[0]["overdue"] is True
    assert api(me).get("/api/tasks/?assignee=me&open=1").data["count"] == 1
    inactive = make_user("gone@example.com", is_active=False)
    assert task(api, admin, tree["france"], assignee=str(inactive.pk)).status_code == 400


def test_complete_closes_the_task_once(api, admin, tree):
    created = task(api, admin, tree["france"]).data
    done = api(admin).post(f"/api/tasks/{created['id']}/complete/")
    assert done.status_code == 200 and done.data["status"] == "done" and done.data["completed_at"]
    assert api(admin).post(f"/api/tasks/{created['id']}/complete/").status_code == 400
    assert Task.objects.count() == 1  # no recurrence, so nothing follows


@pytest.mark.parametrize(
    ("recurrence", "interval", "start", "expected"),
    [
        ("daily", 3, date(2026, 1, 30), date(2026, 2, 2)),
        ("weekly", 2, date(2026, 12, 28), date(2027, 1, 11)),
        ("monthly", 1, date(2026, 1, 31), date(2026, 2, 28)),  # month end clamps
        ("monthly", 1, date(2028, 1, 31), date(2028, 2, 29)),  # leap year
        ("monthly", 13, date(2026, 3, 15), date(2027, 4, 15)),
        ("yearly", 1, date(2028, 2, 29), date(2029, 2, 28)),
    ],
)
def test_recurrence_dates(recurrence, interval, start, expected, tree):
    t = Task(
        domain=tree["france"],
        title="x",
        due_date=start,
        recurrence=recurrence,
        recurrence_interval=interval,
    )
    assert service.next_due(t) == expected


def test_completing_a_repeating_task_creates_the_next_one_once(api, admin, tree):
    created = task(
        api,
        admin,
        tree["france"],
        due_date="2026-01-31",
        recurrence="monthly",
        description="Check backups",
    ).data
    api(admin).post(f"/api/tasks/{created['id']}/complete/")
    original = Task.objects.get(pk=created["id"])
    following = original.next_task
    assert following.status == "to_do" and following.due_date == date(2026, 2, 28)
    assert following.description == "Check backups" and following.last_reminded_on is None
    service.complete(original)  # completing again must not spawn a second copy
    assert Task.objects.count() == 2


def test_links_to_objects_are_checked(api, admin, make_user, tree, grant):
    control = (
        api(admin)
        .post(
            "/api/applied-controls/",
            {"domain": str(tree["france"].pk), "name": "Backup"},
            format="json",
        )
        .data
    )
    far = (
        api(admin)
        .post(
            "/api/applied-controls/", {"domain": str(tree["asia"].pk), "name": "Far"}, format="json"
        )
        .data
    )
    ok = task(
        api,
        admin,
        tree["france"],
        linked_object_type="controls.appliedcontrol",
        linked_object_id=control["id"],
    )
    assert ok.status_code == 201, ok.data
    assert (
        task(
            api,
            admin,
            tree["france"],
            linked_object_type="controls.appliedcontrol",
            linked_object_id=far["id"],
        ).status_code
        == 400
    )
    assert (
        task(
            api, admin, tree["france"], linked_object_type="nope.nope", linked_object_id="1"
        ).status_code
        == 400
    )
    assert (
        task(api, admin, tree["france"], linked_object_type="controls.appliedcontrol").status_code
        == 400
    )
    listing = api(admin).get(
        f"/api/tasks/?linked_object_type=controls.appliedcontrol&linked_object_id={control['id']}"
    )
    assert listing.data["count"] == 1


def make_task(user, domain, due, **extra):
    extra.setdefault("title", "t")
    return Task.objects.create(domain=domain, assignee=user, due_date=due, **extra)


def test_reminder_rules(tree, make_user):
    user = make_user()
    today = date(2026, 6, 10)
    t = make_task(user, tree["france"], today + timedelta(days=3), reminder_days_before=1)
    assert not service.should_remind(t, today)  # still outside the window
    assert service.should_remind(t, today + timedelta(days=2))
    t.last_reminded_on = today + timedelta(days=2)
    assert not service.should_remind(t, today + timedelta(days=2))  # already told today
    assert service.should_remind(t, today + timedelta(days=3))  # again on the day
    t.last_reminded_on = today + timedelta(days=3)
    assert not service.should_remind(t, today + timedelta(days=5))  # overdue, but told recently
    assert service.should_remind(t, today + timedelta(days=10))  # weekly nudge once overdue
    assert not service.should_remind(Task(assignee=None, due_date=today), today)
    assert not service.should_remind(Task(assignee=user, due_date=None), today)


def test_send_reminders_groups_by_person_and_does_not_repeat(tree, make_user):
    ana, ben = make_user("ana@example.com"), make_user("ben@example.com")
    today = date.today()
    make_task(ana, tree["france"], today, title="A1")
    Task.objects.create(
        domain=tree["france"], title="A2", assignee=ana, due_date=today - timedelta(days=2)
    )
    Task.objects.create(
        domain=tree["asia"], title="B1", assignee=ben, due_date=today + timedelta(days=1)
    )
    Task.objects.create(
        domain=tree["asia"], title="Later", assignee=ben, due_date=today + timedelta(days=30)
    )
    Task.objects.create(
        domain=tree["asia"], title="Done", assignee=ben, due_date=today, status="done"
    )
    dry = service.send_reminders(dry_run=True)
    assert dry == {"recipients": 2, "tasks": 3} and mail.outbox == []
    call_command("send_reminders")
    assert sorted(m.to[0] for m in mail.outbox) == ["ana@example.com", "ben@example.com"]
    ana_mail = next(m for m in mail.outbox if m.to == ["ana@example.com"])
    assert (
        "2 tasks" in ana_mail.subject and "A2" in ana_mail.body and "overdue since" in ana_mail.body
    )
    mail.outbox.clear()
    call_command("send_reminders")
    assert mail.outbox == []  # nothing new to say
    assert Task.objects.get(title="B1").last_reminded_on == today
