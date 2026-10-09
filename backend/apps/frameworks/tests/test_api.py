import json

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.frameworks import loader
from apps.frameworks.importers.spec import FrameworkSpec, NodeSpec
from apps.frameworks.models import Framework

from .fixtures import make_scf_workbook

pytestmark = pytest.mark.django_db


def spec(slug="demo", redistributable=True):
    return FrameworkSpec(
        slug=slug,
        name=f"Framework {slug}",
        version="1",
        provider="me",
        redistributable=redistributable,
        nodes=[
            NodeSpec("1", "Group", assessable=False),
            NodeSpec("1.1", "Item", parent_ref="1"),
            NodeSpec("1.2", "Other", parent_ref="1"),
        ],
    )


def test_instance_wide_frameworks_need_a_role_that_can_view_them(api, make_user, tree, grant):
    loader.load(spec())
    nobody, reader = make_user("n@example.com"), make_user("r@example.com")
    grant(reader, "Reader", tree["asia"])
    assert api(nobody).get("/api/frameworks/").data["results"] == []
    listing = api(reader).get("/api/frameworks/").data["results"]
    assert [f["slug"] for f in listing] == ["demo"]
    assert (listing[0]["node_count"], listing[0]["assessable_count"]) == (3, 2)


def test_custom_frameworks_are_scoped_to_their_domain(api, make_user, tree, grant):
    loader.load(spec("fr-only"), domain=tree["france"])
    europe_reader, asia_reader = make_user("e@example.com"), make_user("a@example.com")
    grant(europe_reader, "Reader", tree["europe"])
    grant(asia_reader, "Reader", tree["asia"])
    assert [f["slug"] for f in api(europe_reader).get("/api/frameworks/").data["results"]] == [
        "fr-only"
    ]
    assert api(asia_reader).get("/api/frameworks/").data["results"] == []


def test_nodes_endpoint_returns_the_whole_tree_in_order(api, admin):
    framework = loader.load(spec())
    rows = api(admin).get(f"/api/frameworks/{framework.pk}/nodes/").data
    assert [r["ref_id"] for r in rows] == ["1", "1.1", "1.2"]
    assert str(rows[1]["parent"]) == str(rows[0]["id"])


def test_imported_frameworks_are_read_only_even_for_administrators(api, admin):
    framework = loader.load(spec())
    assert (
        api(admin)
        .patch(f"/api/frameworks/{framework.pk}/", {"name": "x"}, format="json")
        .status_code
        == 400
    )
    node = framework.nodes.get(ref_id="1.1")
    assert (
        api(admin)
        .patch(f"/api/requirement-nodes/{node.pk}/", {"name": "x"}, format="json")
        .status_code
        == 400
    )
    added = api(admin).post(
        "/api/requirement-nodes/",
        {"framework": str(framework.pk), "ref_id": "9", "name": "n"},
        format="json",
    )
    assert added.status_code == 400


def test_derive_then_customise(api, make_user, tree, grant):
    source = loader.load(spec())
    manager = make_user("m@example.com")
    grant(manager, "Manager", tree["europe"])
    outside = api(manager).post(
        f"/api/frameworks/{source.pk}/derive/",
        {"domain": str(tree["asia"].pk), "name": "X"},
        format="json",
    )
    assert outside.status_code == 403
    created = api(manager).post(
        f"/api/frameworks/{source.pk}/derive/",
        {"domain": str(tree["europe"].pk), "name": "Our baseline"},
        format="json",
    )
    assert created.status_code == 201, created.data
    mine = created.data
    assert (mine["slug"], mine["locked"], mine["node_count"]) == ("our-baseline", False, 3)
    # edit the framework, add and change a requirement, refuse a duplicate reference and a bad parent
    assert (
        api(manager)
        .patch(f"/api/frameworks/{mine['id']}/", {"name": "Our baseline v2"}, format="json")
        .status_code
        == 200
    )
    added = api(manager).post(
        "/api/requirement-nodes/",
        {"framework": mine["id"], "ref_id": "2", "name": "Ours"},
        format="json",
    )
    assert added.status_code == 201, added.data
    duplicate = api(manager).post(
        "/api/requirement-nodes/",
        {"framework": mine["id"], "ref_id": "2", "name": "Again"},
        format="json",
    )
    assert duplicate.status_code == 400
    other_parent = source.nodes.get(ref_id="1")
    foreign = api(manager).patch(
        f"/api/requirement-nodes/{added.data['id']}/",
        {"parent": str(other_parent.pk)},
        format="json",
    )
    assert foreign.status_code == 400
    # a cycle is refused
    own = Framework.objects.get(pk=mine["id"])
    group, item = own.nodes.get(ref_id="1"), own.nodes.get(ref_id="1.1")
    cycle = api(manager).patch(
        f"/api/requirement-nodes/{group.pk}/", {"parent": str(item.pk)}, format="json"
    )
    assert cycle.status_code == 400
    # the original is untouched
    assert source.nodes.count() == 3


def test_a_reader_cannot_edit_a_custom_framework(api, make_user, tree, grant):
    framework = loader.load(spec("custom"), domain=tree["europe"])
    reader = make_user()
    grant(reader, "Reader", tree["europe"])
    assert (
        api(reader)
        .patch(f"/api/frameworks/{framework.pk}/", {"name": "x"}, format="json")
        .status_code
        == 403
    )
    node = framework.nodes.get(ref_id="1.1")
    assert (
        api(reader)
        .patch(f"/api/requirement-nodes/{node.pk}/", {"name": "x"}, format="json")
        .status_code
        == 403
    )


def test_export_is_blocked_for_licensed_content_and_roundtrips_otherwise(api, admin, tree):
    licensed = loader.load(spec("licensed", redistributable=False))
    assert api(admin).get(f"/api/frameworks/{licensed.pk}/export/").status_code == 403
    open_one = loader.load(spec("open"))
    response = api(admin).get(f"/api/frameworks/{open_one.pk}/export/")
    assert response.status_code == 200 and "attachment" in response["Content-Disposition"]
    exported = json.loads(response.content)
    assert exported["format"] == "nliuecom-framework/1" and len(exported["nodes"]) == 3
    # the exported file imports into a domain as a custom framework
    upload = SimpleUploadedFile("open.json", response.content)
    imported = api(admin).post(
        "/api/frameworks/import/",
        {"kind": "project", "file": upload, "domain": str(tree["france"].pk)},
        format="multipart",
    )
    assert imported.status_code == 201, imported.data
    assert imported.data["locked"] is False and imported.data["node_count"] == 3


def test_import_endpoint_rules(api, admin, make_user, tree, grant, tmp_path):
    workbook = tmp_path / "scf.xlsx"
    make_scf_workbook(workbook)
    manager = make_user("m@example.com")
    grant(manager, "Domain administrator", tree["europe"])

    def body(name=workbook.name):
        return {"kind": "scf", "file": SimpleUploadedFile(name, workbook.read_bytes())}

    assert (
        api(manager).post("/api/frameworks/import/", body(), format="multipart").status_code == 403
    )
    wrong_type = api(admin).post("/api/frameworks/import/", body("scf.csv"), format="multipart")
    assert wrong_type.status_code == 400
    ok = api(admin).post("/api/frameworks/import/", body(), format="multipart")
    assert ok.status_code == 201, ok.data
    assert (
        ok.data["locked"] and not ok.data["redistributable"] and ok.data["assessable_count"] == 138
    )
    again = api(admin).post("/api/frameworks/import/", body(), format="multipart")
    assert again.status_code == 400 and "already loaded" in str(again.data)
    replaced = api(admin).post(
        "/api/frameworks/import/", {**body(), "replace": "true"}, format="multipart"
    )
    assert replaced.status_code == 201
    domain_scf = api(admin).post(
        "/api/frameworks/import/", {**body(), "domain": str(tree["france"].pk)}, format="multipart"
    )
    assert domain_scf.status_code == 400
    garbage = api(admin).post(
        "/api/frameworks/import/",
        {"kind": "iso27001", "file": SimpleUploadedFile("x.pdf", b"nope")},
        format="multipart",
    )
    assert garbage.status_code == 400 and "could not be read" in str(garbage.data)


def test_mappings_are_listed_per_node(api, admin, tmp_path):
    from apps.frameworks.importers import iso27001, scf

    from .fixtures import make_iso_pages

    workbook = tmp_path / "scf.xlsx"
    make_scf_workbook(workbook)
    scf_framework = loader.load(scf.parse(workbook))
    iso_framework = loader.load(iso27001.parse_pages(make_iso_pages()))
    control = scf_framework.nodes.get(ref_id="AAA-01")
    links = api(admin).get(f"/api/requirement-nodes/{control.pk}/mappings/").data
    assert {link["target_ref"] for link in links} == {
        "4.1",
        "5.1",
        "6.1.2",
        "A.5.1",
        "A.5.4",
        "A.8.34",
    }
    assert {link["target_framework"] for link in links} == {"iso-27001-2022"}
    clause = iso_framework.nodes.get(ref_id="4.1")
    backwards = api(admin).get(f"/api/requirement-nodes/{clause.pk}/mappings/").data
    assert [link["source_ref"] for link in backwards] == ["AAA-01"]
    listing = api(admin).get(f"/api/requirement-mappings/?framework={iso_framework.pk}")
    assert listing.status_code == 200 and listing.data["count"] == 6
    assert api(admin).post("/api/requirement-mappings/", {}, format="json").status_code == 405
