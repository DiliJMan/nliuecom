import pytest
from django.db.models import ProtectedError

from apps.compliance.models import ComplianceAssessment
from apps.frameworks import loader
from apps.frameworks.importers import iso27001, scf
from apps.frameworks.importers.spec import FrameworkSpec, ImportProblem, NodeSpec
from apps.frameworks.tests.fixtures import make_iso_pages, make_scf_workbook

pytestmark = pytest.mark.django_db


@pytest.fixture
def framework(db):
    return loader.load(
        FrameworkSpec(
            slug="demo",
            name="Demo",
            version="1",
            provider="p",
            redistributable=True,
            nodes=[
                NodeSpec("1", "Group", assessable=False),
                NodeSpec("1.1", "First", parent_ref="1"),
                NodeSpec("1.2", "Second", parent_ref="1"),
                NodeSpec("2", "Third"),
            ],
        )
    )


def create(api, user, domain, framework, **extra):
    payload = {
        "domain": str(domain.pk),
        "name": "Annual review",
        "framework": str(framework.pk),
        **extra,
    }
    return api(user).post("/api/compliance-assessments/", payload, format="json")


def test_creating_an_assessment_adds_one_row_per_assessable_requirement(
    api, admin, tree, framework
):
    response = create(api, admin, tree["france"], framework)
    assert response.status_code == 201, response.data
    assessment = ComplianceAssessment.objects.get()
    refs = sorted(assessment.requirement_assessments.values_list("requirement__ref_id", flat=True))
    assert refs == ["1.1", "1.2", "2"]  # the group node is not assessed
    assert (
        response.data["summary"]["total"] == 3 and response.data["summary"]["assessed_percent"] == 0
    )


def test_summary_counts_results_and_ignores_not_applicable(api, admin, tree, framework):
    created = create(api, admin, tree["france"], framework).data
    rows = (
        api(admin)
        .get(f"/api/requirement-assessments/?compliance_assessment={created['id']}")
        .data["results"]
    )
    by_ref = {r["ref_id"]: r for r in rows}
    for ref, result in (("1.1", "compliant"), ("1.2", "not_applicable")):
        patched = api(admin).patch(
            f"/api/requirement-assessments/{by_ref[ref]['id']}/", {"result": result}, format="json"
        )
        assert patched.status_code == 200
    summary = api(admin).get(f"/api/compliance-assessments/{created['id']}/").data["summary"]
    assert summary["counts"]["compliant"] == 1 and summary["counts"]["not_applicable"] == 1
    assert (
        summary["applicable"] == 2
        and summary["assessed_percent"] == 50
        and summary["compliant_percent"] == 50
    )


def test_only_people_with_change_rights_can_answer(api, admin, make_user, tree, grant, framework):
    created = create(api, admin, tree["france"], framework).data
    row = (
        api(admin)
        .get(f"/api/requirement-assessments/?compliance_assessment={created['id']}")
        .data["results"][0]
    )
    reader, contributor, outsider = (
        make_user("r@example.com"),
        make_user("c@example.com"),
        make_user("o@example.com"),
    )
    grant(reader, "Reader", tree["europe"])
    grant(contributor, "Contributor", tree["france"])
    grant(outsider, "Contributor", tree["asia"])
    url = f"/api/requirement-assessments/{row['id']}/"
    assert api(reader).patch(url, {"result": "compliant"}, format="json").status_code == 403
    assert (
        api(contributor)
        .patch(url, {"result": "compliant", "observation": "Checked"}, format="json")
        .status_code
        == 200
    )
    assert api(outsider).patch(url, {"result": "compliant"}, format="json").status_code == 404
    assert api(admin).patch(url, {"result": "invented"}, format="json").status_code == 400
    assert api(admin).delete(url).status_code == 405
    assert api(admin).post("/api/requirement-assessments/", {}, format="json").status_code == 405


def test_framework_visibility_is_checked_on_create(api, make_user, tree, grant, framework):
    contributor, nobody = make_user("c@example.com"), make_user("n@example.com")
    grant(contributor, "Manager", tree["france"])
    assert create(api, contributor, tree["france"], framework).status_code == 201
    from apps.access.models import Role, RoleAssignment

    role = Role.objects.create(
        name="Assess only",
        permissions=["compliance.complianceassessment:add", "compliance.complianceassessment:view"],
    )
    RoleAssignment.objects.create(user=nobody, role=role, domain=tree["france"])
    refused = create(api, nobody, tree["france"], framework)
    assert refused.status_code == 400 and "framework" in refused.data
    assert create(api, contributor, tree["asia"], framework).status_code == 403


def test_the_framework_cannot_change_and_cannot_be_replaced_while_in_use(
    api, admin, tree, framework
):
    created = create(api, admin, tree["france"], framework).data
    other = loader.load(
        FrameworkSpec(
            slug="other", name="Other", version="1", provider="p", nodes=[NodeSpec("1", "x")]
        )
    )
    switch = api(admin).patch(
        f"/api/compliance-assessments/{created['id']}/", {"framework": str(other.pk)}, format="json"
    )
    assert switch.status_code == 400
    with pytest.raises(ImportProblem, match="used by compliance assessments"):
        loader.load(
            FrameworkSpec(
                slug="demo", name="Demo", version="2", provider="p", nodes=[NodeSpec("1", "x")]
            ),
            replace=True,
        )
    assert api(admin).delete(f"/api/frameworks/{framework.pk}/").status_code == 409
    with pytest.raises(ProtectedError):
        framework.delete()


def test_links_to_controls_and_evidence_stay_within_reach(api, admin, tree, framework):
    created = create(api, admin, tree["france"], framework).data
    row = (
        api(admin)
        .get(f"/api/requirement-assessments/?compliance_assessment={created['id']}")
        .data["results"][0]
    )
    mine = (
        api(admin)
        .post(
            "/api/applied-controls/",
            {"domain": str(tree["france"].pk), "name": "Mine"},
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
    ev = (
        api(admin)
        .post(
            "/api/evidence/",
            {"domain": str(tree["europe"].pk), "name": "Policy", "url": "https://example.org/p"},
            format="json",
        )
        .data
    )
    url = f"/api/requirement-assessments/{row['id']}/"
    ok = api(admin).patch(
        url, {"applied_controls": [mine["id"]], "evidence": [ev["id"]]}, format="json"
    )
    assert ok.status_code == 200, ok.data
    assert (
        api(admin).patch(url, {"applied_controls": [far["id"]]}, format="json").status_code == 400
    )


def test_workbench_returns_the_whole_tree_with_answers(api, admin, tree, framework):
    created = create(api, admin, tree["france"], framework).data
    rows = api(admin).get(f"/api/compliance-assessments/{created['id']}/workbench/").data
    assert [r["ref_id"] for r in rows] == ["1", "1.1", "1.2", "2"]
    assert rows[0]["assessment"] is None and rows[0]["assessable"] is False
    assert rows[1]["assessment"]["result"] == "not_assessed" and rows[1]["parent"] == rows[0]["id"]


def test_suggestions_come_from_mapped_requirements_in_another_assessment(
    api, admin, tree, tmp_path
):
    workbook = tmp_path / "scf.xlsx"
    make_scf_workbook(workbook)
    scf_framework = loader.load(scf.parse(workbook))
    iso_framework = loader.load(iso27001.parse_pages(make_iso_pages()))
    scf_assessment = create(api, admin, tree["france"], scf_framework, name="SCF").data
    iso_assessment = create(api, admin, tree["france"], iso_framework, name="ISO").data
    rows = (
        api(admin)
        .get(
            f"/api/requirement-assessments/?compliance_assessment={scf_assessment['id']}&search=AAA-01&page_size=10"
        )
        .data["results"]
    )
    control = next(r for r in rows if r["ref_id"] == "AAA-01")
    api(admin).patch(
        f"/api/requirement-assessments/{control['id']}/", {"result": "compliant"}, format="json"
    )
    hints = (
        api(admin)
        .get(
            f"/api/compliance-assessments/{iso_assessment['id']}/suggestions/?source={scf_assessment['id']}"
        )
        .data
    )
    by_requirement = {h["requirement"]: h for h in hints}
    clause = iso_framework.nodes.get(ref_id="A.5.1")
    assert str(clause.pk) in by_requirement
    assert by_requirement[str(clause.pk)]["from"] == [
        {"ref_id": "AAA-01", "name": "Alpha Practices control 1", "result": "compliant"}
    ]
    # an answered requirement no longer gets a hint, and the source must be named and visible
    answered = (
        api(admin)
        .get(
            f"/api/requirement-assessments/?compliance_assessment={iso_assessment['id']}&search=A.5.1"
        )
        .data["results"][0]
    )
    api(admin).patch(
        f"/api/requirement-assessments/{answered['id']}/",
        {"result": "non_compliant"},
        format="json",
    )
    after = (
        api(admin)
        .get(
            f"/api/compliance-assessments/{iso_assessment['id']}/suggestions/?source={scf_assessment['id']}"
        )
        .data
    )
    assert str(clause.pk) not in {h["requirement"] for h in after}
    assert (
        api(admin)
        .get(f"/api/compliance-assessments/{iso_assessment['id']}/suggestions/")
        .status_code
        == 400
    )
