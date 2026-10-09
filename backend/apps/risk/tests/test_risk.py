import pytest
from django.core.exceptions import ValidationError

from apps.risk.matrix import default_matrix, validate_matrix
from apps.risk.models import RiskMatrix

pytestmark = pytest.mark.django_db


@pytest.fixture
def matrix():
    return RiskMatrix.objects.get(name="Default 5x5")


def assessment(api, user, domain, matrix, **extra):
    return api(user).post(
        "/api/risk-assessments/",
        {"domain": str(domain.pk), "name": "2026 review", "matrix": str(matrix.pk), **extra},
        format="json",
    )


def scenario(api, user, ra, **extra):
    return api(user).post(
        "/api/risk-scenarios/",
        {"risk_assessment": ra["id"], "name": "Ransomware", **extra},
        format="json",
    )


def test_default_matrix_is_built_in_and_valid(matrix):
    assert matrix.builtin and len(matrix.probability) == 5 and len(matrix.impact) == 5
    validate_matrix(matrix.probability, matrix.impact, matrix.levels, matrix.grid)
    assert matrix.level_for(0, 0)["name"] == "Very low"
    assert matrix.level_for(4, 4)["name"] == "Critical"
    assert matrix.level_for(None, 2) is None and matrix.level_for(5, 0) is None
    # a higher step on either scale never lowers the level
    for p in range(5):
        for i in range(4):
            assert matrix.grid[p][i] <= matrix.grid[p][i + 1]
            assert matrix.grid[i][p] <= matrix.grid[i + 1][p]


@pytest.mark.parametrize(
    "mutate",
    [
        lambda m: m.update(probability=[{"name": "only one"}]),
        lambda m: m.update(impact=[{"name": ""}, {"name": "b"}]),
        lambda m: m["levels"].__setitem__(0, {"name": "x", "colour": "red"}),
        lambda m: m.update(grid=m["grid"][:-1]),
        lambda m: m["grid"][0].__setitem__(0, 9),
        lambda m: m["grid"][0].__setitem__(0, True),
    ],
)
def test_matrix_rules(mutate):
    data = default_matrix()
    mutate(data)
    with pytest.raises(ValidationError):
        validate_matrix(data["probability"], data["impact"], data["levels"], data["grid"])


def test_matrix_api_protects_the_builtin_and_validates(api, admin, make_user, tree, grant, matrix):
    client = api(admin)
    assert (
        client.patch(f"/api/risk-matrices/{matrix.pk}/", {"name": "x"}, format="json").status_code
        == 400
    )
    assert client.delete(f"/api/risk-matrices/{matrix.pk}/").status_code == 400
    custom = default_matrix() | {"name": "Mine", "description": ""}
    created = client.post("/api/risk-matrices/", custom, format="json")
    assert created.status_code == 201, created.data
    custom["grid"] = [[0, 0], [0, 0]]
    assert (
        client.post("/api/risk-matrices/", {**custom, "name": "Broken"}, format="json").status_code
        == 400
    )
    contributor = make_user()
    grant(contributor, "Contributor", tree["europe"])
    assert api(contributor).get("/api/risk-matrices/").status_code == 200
    assert (
        api(contributor)
        .post("/api/risk-matrices/", {**default_matrix(), "name": "Sneaky"}, format="json")
        .status_code
        == 403
    )


def test_scenarios_rate_against_the_matrix(api, admin, tree, matrix):
    ra = assessment(api, admin, tree["france"], matrix).data
    created = scenario(
        api,
        admin,
        ra,
        current_probability=3,
        current_impact=4,
        residual_probability=1,
        residual_impact=2,
        treatment="mitigate",
    )
    assert created.status_code == 201, created.data
    assert created.data["current_level"]["name"] == "Critical"
    assert created.data["residual_level"]["name"] == "Medium"  # (1 + 1) x (2 + 1) = 6
    assert scenario(api, admin, ra, current_probability=5).status_code == 400
    assert scenario(api, admin, ra, residual_impact=9).status_code == 400
    unrated = scenario(api, admin, ra, name="Unrated")
    assert unrated.data["current_level"] is None


def test_heatmap_counts_cells_and_unrated(api, admin, tree, matrix):
    ra = assessment(api, admin, tree["france"], matrix).data
    scenario(
        api,
        admin,
        ra,
        name="a",
        current_probability=3,
        current_impact=4,
        residual_probability=1,
        residual_impact=1,
    )
    scenario(api, admin, ra, name="b", current_probability=3, current_impact=4)
    scenario(api, admin, ra, name="c")
    heat = api(admin).get(f"/api/risk-assessments/{ra['id']}/heatmap/").data
    assert heat["current"][3][4] == 2 and heat["residual"][1][1] == 1 and heat["unrated"] == 1
    assert api(admin).get(f"/api/risk-assessments/{ra['id']}/").data["scenario_count"] == 3


def test_scenario_permissions_follow_the_assessments_domain(
    api, admin, make_user, tree, grant, matrix
):
    ra = assessment(api, admin, tree["france"], matrix).data
    reader, contributor, outsider = (
        make_user("r@example.com"),
        make_user("c@example.com"),
        make_user("o@example.com"),
    )
    grant(reader, "Reader", tree["europe"])
    grant(contributor, "Contributor", tree["france"])
    grant(outsider, "Contributor", tree["asia"])
    assert scenario(api, reader, ra).status_code == 403
    made = scenario(api, contributor, ra)
    assert made.status_code == 201
    assert api(reader).get("/api/risk-scenarios/").data["count"] == 1
    assert api(outsider).get("/api/risk-scenarios/").data["count"] == 0
    assert scenario(api, outsider, ra).status_code == 403
    assert (
        api(reader)
        .patch(f"/api/risk-scenarios/{made.data['id']}/", {"name": "x"}, format="json")
        .status_code
        == 403
    )


def test_scenarios_link_only_reachable_assets_and_controls(
    api, admin, make_user, tree, grant, matrix
):
    ra = assessment(api, admin, tree["france"], matrix).data
    own_asset = (
        api(admin)
        .post("/api/assets/", {"domain": str(tree["france"].pk), "name": "App"}, format="json")
        .data
    )
    far_asset = (
        api(admin)
        .post("/api/assets/", {"domain": str(tree["asia"].pk), "name": "Far"}, format="json")
        .data
    )
    control = (
        api(admin)
        .post(
            "/api/applied-controls/",
            {"domain": str(tree["europe"].pk), "name": "Backup"},
            format="json",
        )
        .data
    )
    ok = scenario(api, admin, ra, assets=[own_asset["id"]], applied_controls=[control["id"]])
    assert ok.status_code == 201, ok.data
    assert scenario(api, admin, ra, assets=[far_asset["id"]]).status_code == 400


def test_assessment_rules(api, admin, tree, matrix):
    ra = assessment(api, admin, tree["france"], matrix).data
    scenario(api, admin, ra)
    other = (
        api(admin)
        .post("/api/risk-matrices/", default_matrix() | {"name": "Other"}, format="json")
        .data
    )
    switch = api(admin).patch(
        f"/api/risk-assessments/{ra['id']}/", {"matrix": other["id"]}, format="json"
    )
    assert switch.status_code == 400
    second = scenario(api, admin, ra, name="two").data
    other_ra = assessment(api, admin, tree["france"], matrix, name="Second").data
    move = api(admin).patch(
        f"/api/risk-scenarios/{second['id']}/", {"risk_assessment": other_ra["id"]}, format="json"
    )
    assert move.status_code == 400
    assert api(admin).delete(f"/api/risk-matrices/{matrix.pk}/").status_code == 400
