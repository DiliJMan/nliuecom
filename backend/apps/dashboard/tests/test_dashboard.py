from datetime import date, timedelta

import pytest

from apps.risk.models import RiskMatrix
from apps.tasks.models import Task

pytestmark = pytest.mark.django_db


def test_dashboard_counts_only_what_the_caller_can_see(api, admin, make_user, tree, grant):
    matrix = RiskMatrix.objects.get(name="Default 5x5")
    post = lambda url, body: api(admin).post(url, body, format="json").data  # noqa: E731
    for domain, name in ((tree["france"], "fr"), (tree["asia"], "as")):
        post("/api/assets/", {"domain": str(domain.pk), "name": name})
        post("/api/applied-controls/", {"domain": str(domain.pk), "name": name, "status": "active"})
        ra = post(
            "/api/risk-assessments/",
            {"domain": str(domain.pk), "name": name, "matrix": str(matrix.pk)},
        )
        post(
            "/api/risk-scenarios/",
            {
                "risk_assessment": ra["id"],
                "name": name,
                "current_probability": 4,
                "current_impact": 4,
            },
        )
        post("/api/risk-scenarios/", {"risk_assessment": ra["id"], "name": name + "2"})
    reader = make_user()
    grant(reader, "Reader", tree["europe"])
    data = api(reader).get("/api/dashboard/").data
    assert data["assets"] == 1 and data["controls"] == {"total": 1, "by_status": {"active": 1}}
    assert data["risk"]["scenarios"] == 2 and data["risk"]["unrated"] == 1
    assert data["risk"]["by_level"] == [{"name": "Critical", "colour": "#b3261e", "count": 1}]
    everything = api(admin).get("/api/dashboard/").data
    assert everything["assets"] == 2 and everything["risk"]["scenarios"] == 4


def test_dashboard_task_numbers_are_personal(api, make_user, tree):
    me, other = make_user("me@example.com", is_superuser=True), make_user("o@example.com")
    today = date.today()
    for who, due in (
        (me, today - timedelta(days=1)),
        (me, today + timedelta(days=3)),
        (me, today + timedelta(days=30)),
        (other, today),
    ):
        Task.objects.create(domain=tree["france"], title="t", assignee=who, due_date=due)
    data = api(me).get("/api/dashboard/").data["tasks"]
    assert data == {"open": 3, "overdue": 1, "due_this_week": 1}


def test_dashboard_needs_a_signed_in_user():
    from rest_framework.test import APIClient

    assert APIClient().get("/api/dashboard/").status_code in {401, 403}
