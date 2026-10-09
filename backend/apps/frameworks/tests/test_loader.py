import pytest

from apps.audit.models import AuditEvent
from apps.frameworks import loader
from apps.frameworks.importers import iso27001, scf
from apps.frameworks.importers.spec import FrameworkSpec, ImportProblem, NodeSpec
from apps.frameworks.models import Framework, RequirementMapping, RequirementNode

from .fixtures import make_iso_pages, make_scf_workbook

pytestmark = pytest.mark.django_db


def small_spec(slug="demo", **kwargs):
    return FrameworkSpec(
        slug=slug,
        name="Demo",
        version="1",
        provider="me",
        redistributable=True,
        nodes=[NodeSpec("1", "Group", assessable=False), NodeSpec("1.1", "Item", parent_ref="1")],
        **kwargs,
    )


def test_load_creates_locked_framework_with_tree():
    framework = loader.load(small_spec())
    assert framework.locked and framework.domain is None
    item = RequirementNode.objects.get(framework=framework, ref_id="1.1")
    assert item.parent.ref_id == "1" and item.assessable
    assert AuditEvent.objects.filter(
        object_type="frameworks.framework", changes__requirements_loaded=2
    ).exists()


def test_load_refuses_to_overwrite_unless_asked():
    loader.load(small_spec())
    with pytest.raises(ImportProblem, match="already loaded"):
        loader.load(small_spec())
    replaced = loader.load(small_spec(), replace=True)
    assert Framework.objects.filter(slug="demo").count() == 1 and replaced.nodes.count() == 2


def test_load_into_a_domain_gives_an_editable_custom_framework(tree):
    framework = loader.load(small_spec(), domain=tree["europe"])
    assert framework.domain == tree["europe"] and framework.locked is False
    # the same slug can exist instance-wide and in a domain
    assert loader.load(small_spec()).locked


def test_scf_and_iso_loaded_together_get_mapped(tmp_path):
    path = tmp_path / "scf.xlsx"
    make_scf_workbook(path)
    loader.load(scf.parse(path))
    assert RequirementMapping.objects.count() == 0  # nothing to map to yet
    loader.load(iso27001.parse_pages(make_iso_pages()))
    # AAA-01 maps to ISO 4.1, 5.1, 6.1.2, A.5.1, A.5.4 and A.8.34
    links = RequirementMapping.objects.filter(source__ref_id="AAA-01")
    assert sorted(links.values_list("target__ref_id", flat=True)) == [
        "4.1",
        "5.1",
        "6.1.2",
        "A.5.1",
        "A.5.4",
        "A.8.34",
    ]
    assert set(links.values_list("origin", flat=True)) == {"scf-2026.3"}
    assert loader.sync_mappings() == 0  # running again adds nothing


def test_derive_copies_the_tree_and_inherits_licence_flags(tree):
    source = loader.load(small_spec(licence_note="Keep local.", attribution="Someone"))
    source.redistributable = False
    source.save()
    copy = loader.derive(source, domain=tree["france"], name="Our version", slug="ours")
    assert copy.derived_from == source and copy.domain == tree["france"] and not copy.locked
    assert copy.redistributable is False and copy.licence_note == "Keep local."
    nodes = {n.ref_id: n for n in copy.nodes.all()}
    assert (
        nodes["1.1"].parent == nodes["1"]
        and nodes["1.1"].pk != RequirementNode.objects.get(framework=source, ref_id="1.1").pk
    )
