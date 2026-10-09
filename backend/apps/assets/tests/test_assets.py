import pytest

from apps.assets.models import Asset
from apps.customfields.models import CustomFieldDefinition

pytestmark = pytest.mark.django_db


def make(api, user, domain, **extra):
    payload = {"domain": str(domain.pk), "name": "Payroll system", **extra}
    return api(user).post("/api/assets/", payload, format="json")


def test_assets_are_scoped_to_the_users_domains(api, make_user, tree, grant):
    contributor, outsider = make_user("c@example.com"), make_user("o@example.com")
    grant(contributor, "Contributor", tree["europe"])
    grant(outsider, "Reader", tree["asia"])
    created = make(api, contributor, tree["france"])
    assert created.status_code == 201, created.data
    assert api(contributor).get("/api/assets/").data["count"] == 1
    assert api(outsider).get("/api/assets/").data["count"] == 0
    assert api(outsider).get(f"/api/assets/{created.data['id']}/").status_code == 404
    assert make(api, contributor, tree["asia"]).status_code == 403


def test_dependencies_must_stay_inside_reach(api, admin, make_user, tree, grant):
    own = make(api, admin, tree["france"], name="App").data
    parent_level = make(api, admin, tree["europe"], name="Shared platform").data
    elsewhere = make(api, admin, tree["asia"], name="Asia system").data
    manager = make_user()
    grant(manager, "Manager", tree["europe"])
    grant(manager, "Reader", tree["asia"])
    ok = api(manager).patch(
        f"/api/assets/{own['id']}/", {"depends_on": [parent_level["id"]]}, format="json"
    )
    assert ok.status_code == 200, ok.data
    bad = api(manager).patch(
        f"/api/assets/{own['id']}/", {"depends_on": [elsewhere["id"]]}, format="json"
    )
    assert bad.status_code == 400 and "depends_on" in bad.data


def test_a_viewer_of_nothing_cannot_link_to_an_asset(api, admin, make_user, tree, grant):
    shared = make(api, admin, tree["europe"], name="Shared").data
    mine = make(api, admin, tree["france"], name="Mine").data
    contributor = make_user()
    grant(contributor, "Contributor", tree["france"])  # no rights on Europe, where "Shared" lives
    response = api(contributor).patch(
        f"/api/assets/{mine['id']}/", {"depends_on": [shared["id"]]}, format="json"
    )
    assert response.status_code == 400 and "cannot view" in str(response.data["depends_on"])


def test_dependency_loops_are_refused(api, admin, tree):
    a = make(api, admin, tree["france"], name="A").data
    b = make(api, admin, tree["france"], name="B", depends_on=[a["id"]]).data
    c = make(api, admin, tree["france"], name="C", depends_on=[b["id"]]).data
    loop = api(admin).patch(f"/api/assets/{a['id']}/", {"depends_on": [c["id"]]}, format="json")
    assert loop.status_code == 400
    self_loop = api(admin).patch(
        f"/api/assets/{a['id']}/", {"depends_on": [a["id"]]}, format="json"
    )
    assert self_loop.status_code == 400


def test_field_rules(api, admin, tree):
    assert make(api, admin, tree["france"], confidentiality=5).status_code == 400
    assert make(api, admin, tree["france"], confidentiality=3, integrity=1).status_code == 201
    assert make(api, admin, tree["france"], link="javascript:alert(1)").status_code == 400
    assert (
        make(api, admin, tree["france"], link="https://wiki.example.org/asset").status_code == 201
    )
    assert make(api, admin, tree["france"], type="spaceship").status_code == 400


def test_custom_fields_apply_to_assets(api, admin, tree):
    CustomFieldDefinition.objects.create(
        object_type="assets.asset",
        key="cost_centre",
        label="Cost centre",
        field_type="text",
        required=True,
    )
    assert make(api, admin, tree["france"]).status_code == 400
    ok = make(api, admin, tree["france"], custom_fields={"cost_centre": "CC-9"})
    assert ok.status_code == 201 and ok.data["custom_fields"] == {"cost_centre": "CC-9"}


def test_filter_search_and_order(api, admin, tree):
    make(api, admin, tree["france"], name="Zeta", type="primary")
    make(api, admin, tree["france"], name="Alpha", ref_id="X-1")
    make(api, admin, tree["asia"], name="Beta")
    client = api(admin)
    names = lambda url: [r["name"] for r in client.get(url).data["results"]]  # noqa: E731
    assert names("/api/assets/?ordering=name") == ["Alpha", "Beta", "Zeta"]
    assert names("/api/assets/?ordering=-name") == ["Zeta", "Beta", "Alpha"]
    assert names(f"/api/assets/?domain={tree['asia'].pk}") == ["Beta"]
    assert names("/api/assets/?type=primary") == ["Zeta"]
    assert names("/api/assets/?search=x-1") == ["Alpha"]
    assert (
        names("/api/assets/?ordering=secret_field") != []
    )  # unknown ordering is ignored, not an error


def test_deleting_changes_are_audited(api, admin, tree):
    asset = make(api, admin, tree["france"]).data
    api(admin).patch(f"/api/assets/{asset['id']}/", {"description": "Runs payroll"}, format="json")
    trail = api(admin).get(f"/api/audit/trail/assets.asset/{asset['id']}/").data
    assert [e["action"] for e in trail] == ["update", "create"]
    assert Asset.objects.count() == 1
