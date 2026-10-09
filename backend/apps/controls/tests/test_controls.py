import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.frameworks import loader
from apps.frameworks.importers.spec import FrameworkSpec, NodeSpec

pytestmark = pytest.mark.django_db


def control(api, user, domain, **extra):
    return api(user).post(
        "/api/applied-controls/",
        {"domain": str(domain.pk), "name": "MFA everywhere", **extra},
        format="json",
    )


def test_controls_are_scoped_and_validated(api, admin, make_user, tree, grant):
    contributor = make_user()
    grant(contributor, "Contributor", tree["europe"])
    ok = control(
        api,
        contributor,
        tree["france"],
        status="active",
        category="technical",
        priority=2,
        effort="m",
        control_impact=4,
    )
    assert ok.status_code == 201, ok.data
    assert control(api, contributor, tree["asia"]).status_code == 403
    for bad in (
        {"priority": 9},
        {"control_impact": 0},
        {"status": "nope"},
        {"effort": "huge"},
        {"link": "ftp://x"},
    ):
        assert control(api, admin, tree["france"], **bad).status_code == 400, bad


def test_reference_node_must_be_visible(api, admin, make_user, tree, grant):
    framework = loader.load(
        FrameworkSpec(slug="f", name="F", version="1", provider="p", nodes=[NodeSpec("1", "Item")])
    )
    node = framework.nodes.get()
    contributor, nobody = make_user("c@example.com"), make_user("n@example.com")
    grant(contributor, "Contributor", tree["france"])
    ok = control(api, contributor, tree["france"], reference_node=str(node.pk))
    assert ok.status_code == 201 and ok.data["reference_node_ref"] == "1"
    from apps.access.models import Role, RoleAssignment

    role = Role.objects.create(
        name="Writer only",
        permissions=["controls.appliedcontrol:add", "controls.appliedcontrol:view"],
    )
    RoleAssignment.objects.create(user=nobody, role=role, domain=tree["france"])
    hidden = control(api, nobody, tree["france"], reference_node=str(node.pk))
    assert hidden.status_code == 400


def evidence(api, user, domain, **extra):
    return api(user).post(
        "/api/evidence/", {"domain": str(domain.pk), "name": "Policy PDF", **extra}, format="json"
    )


def test_evidence_needs_a_file_or_a_link(api, admin, tree):
    assert evidence(api, admin, tree["france"]).status_code == 400
    assert evidence(api, admin, tree["france"], url="https://example.org/policy").status_code == 201
    assert evidence(api, admin, tree["france"], url="javascript:alert(1)").status_code == 400


def test_evidence_links_controls_and_attachments_within_reach(api, admin, make_user, tree, grant):
    mine = control(api, admin, tree["france"]).data
    foreign = control(api, admin, tree["asia"], name="Asia control").data
    upload = api(admin).post(
        "/api/attachments/",
        {"domain": str(tree["france"].pk), "file": SimpleUploadedFile("p.pdf", b"%PDF-1")},
        format="multipart",
    )
    other_upload = api(admin).post(
        "/api/attachments/",
        {"domain": str(tree["asia"].pk), "file": SimpleUploadedFile("q.pdf", b"%PDF-2")},
        format="multipart",
    )
    good = evidence(
        api, admin, tree["france"], attachment=upload.data["id"], applied_controls=[mine["id"]]
    )
    assert good.status_code == 201, good.data
    assert good.data["attachment_name"] == "p.pdf"
    assert (
        evidence(api, admin, tree["france"], attachment=other_upload.data["id"]).status_code == 400
    )
    assert (
        evidence(
            api, admin, tree["france"], url="https://x.org", applied_controls=[foreign["id"]]
        ).status_code
        == 400
    )
    listing = api(admin).get(f"/api/evidence/?applied_controls={mine['id']}")
    assert listing.data["count"] == 1


def test_evidence_is_hidden_from_other_domains(api, admin, make_user, tree, grant):
    created = evidence(api, admin, tree["france"], url="https://example.org/x").data
    reader = make_user()
    grant(reader, "Reader", tree["asia"])
    assert api(reader).get(f"/api/evidence/{created['id']}/").status_code == 404
