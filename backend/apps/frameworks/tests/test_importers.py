import json

import pytest

from apps.frameworks.importers import iso27001, projectjson, scf
from apps.frameworks.importers.spec import FrameworkSpec, ImportProblem, NodeSpec
from apps.frameworks.importers.text import build_vocabulary, join_wrapped, repair_kerning

from .fixtures import make_iso_pages, make_scf_workbook


def test_join_wrapped_closes_split_words_but_keeps_prefix_hyphens():
    assert join_wrapped(["secu -", "rity"]) == "security"
    assert join_wrapped(["the fa-", "cilities"]) == "the facilities"
    assert join_wrapped(["the re-", "assignment"]) == "the re-assignment"
    assert join_wrapped(["plain", "words"]) == "plain words"
    assert join_wrapped(["", " "]) == ""


def test_repair_kerning_joins_only_known_split_words():
    text = "information appears here and information again. A single infor mation split. Go to day."
    vocabulary = build_vocabulary(text + " today today")
    fixed = repair_kerning(text, vocabulary)
    assert "infor mation" not in fixed and "A single information split" in fixed
    assert (
        "Go to day" in fixed or "Go today" in fixed
    )  # both words are real, so either is tolerated
    assert repair_kerning("no split here", vocabulary) == "no split here"


# --- SCF ----------------------------------------------------------------------------------


def test_scf_parse_builds_domains_controls_parents_and_mappings(tmp_path):
    path = tmp_path / "scf.xlsx"
    make_scf_workbook(path)
    spec = scf.parse(path)
    spec.validate()
    assert (spec.slug, spec.version, spec.redistributable) == ("scf-2026.3", "2026.3", False)
    by_ref = {n.ref_id: n for n in spec.nodes}
    assert [n.ref_id for n in spec.nodes if not n.assessable] == ["AAA", "BBB", "CCC"]
    assert by_ref["AAA"].name == "Alpha Practices"
    assert by_ref["AAA-02"].parent_ref == "AAA"
    assert by_ref["AAA-01.1"].parent_ref == "AAA-01"  # a sub-control hangs under its control
    assert by_ref["AAA-01"].weight == 10  # clamped from 99
    assert by_ref["AAA-01.1"].weight == 1  # unparseable weight falls back
    maps = by_ref["AAA-01"].extra["maps_to"]
    assert maps["iso-27001-2022"] == ["4.1", "5.1", "6.1.2", "A.5.1", "A.5.4", "A.8.34"]
    assert maps["nist-csf-2.0"] == ["GV", "GV.OC-01"]
    assert "maps_to" not in by_ref["AAA-02"].extra
    assert by_ref["AAA-02"].extra["question"].startswith("Does the organisation")


def test_scf_rejects_other_workbooks(tmp_path):
    wrong_sheet = tmp_path / "a.xlsx"
    make_scf_workbook(wrong_sheet, sheet="Something else")
    with pytest.raises(ImportProblem, match="No sheet named"):
        scf.parse(wrong_sheet)
    missing_column = tmp_path / "b.xlsx"
    make_scf_workbook(missing_column, drop="SCF #")
    with pytest.raises(ImportProblem, match="columns are missing"):
        scf.parse(missing_column)
    too_small = tmp_path / "c.xlsx"
    make_scf_workbook(too_small, controls_per_domain=3)
    with pytest.raises(ImportProblem, match="Far fewer"):
        scf.parse(too_small)
    not_a_workbook = tmp_path / "d.xlsx"
    not_a_workbook.write_text("plain text")
    with pytest.raises(ImportProblem, match="could not be opened"):
        scf.parse(not_a_workbook)


# --- ISO 27001 ------------------------------------------------------------------------------


def test_iso_parse_pages_builds_clauses_and_all_93_controls():
    spec = iso27001.parse_pages(make_iso_pages(), source="test")
    spec.validate()
    by_ref = {n.ref_id: n for n in spec.nodes}
    assert (spec.slug, spec.redistributable) == ("iso-27001-2022", False)
    assert sum(1 for n in spec.nodes if n.ref_id.startswith("A.") and n.assessable) == 93
    assert by_ref["6.1"].assessable is False and by_ref["6.1.2"].parent_ref == "6.1"
    assert by_ref["4"].parent_ref is None and by_ref["4.1"].parent_ref == "4"
    assert by_ref["A.5"].name == "Organizational controls" and by_ref["A.5.1"].parent_ref == "A.5"
    # wrapped lines are joined, split words closed, list items kept on their own lines
    assert by_ref["4.1"].description.splitlines() == [
        "The organization shall consider things.",
        "a) the first item;",
        "b) the second item that wraps over two lines with a split word in it.",
    ]
    assert by_ref["5.2"].description.endswith("NOTE A policy is short.")
    # annex quirks: split title, stray space in the number, glued "Control"
    assert by_ref["A.5.3"].name == "Handling of example items"
    assert by_ref["A.5.3"].description == "Text for 5.3 shall be defined."
    assert by_ref["A.7.3"].name == "Quiet rooms"
    assert by_ref["A.8.18"].name == "Spare tools"
    assert by_ref["A.8.34"].name == "Title 8.34"
    # 5.2 is missing from the synthetic contents page, as three entries are in the real file
    assert any("5.2" in note for note in spec.notes)


def test_iso_parse_refuses_incomplete_or_foreign_documents():
    with pytest.raises(ImportProblem, match="Annex A theme 6"):
        iso27001.parse_pages(make_iso_pages(drop_control=(6, 4)))
    with pytest.raises(ImportProblem, match="does not look like"):
        iso27001.parse_pages(make_iso_pages(bogus=True))


def test_iso_parse_reports_unreadable_files(tmp_path):
    broken = tmp_path / "x.pdf"
    broken.write_bytes(b"not a pdf")
    with pytest.raises(ImportProblem, match="could not be read"):
        iso27001.parse(broken)


# --- project file -----------------------------------------------------------------------------


def _project_file(**overrides):
    data = {
        "format": "nliuecom-framework/1",
        "framework": {"slug": "acme", "name": "Acme baseline", "version": "1"},
        "nodes": [
            {"ref_id": "1", "name": "Group", "assessable": False},
            {"ref_id": "1.1", "name": "Item", "parent": "1", "weight": 50},
        ],
    }
    data.update(overrides)
    return data


def test_project_file_parses_and_validates():
    spec = projectjson.from_dict(_project_file())
    spec.validate()
    assert [n.ref_id for n in spec.nodes] == ["1", "1.1"]
    assert spec.nodes[1].parent_ref == "1" and spec.nodes[1].weight == 10  # clamped
    assert spec.redistributable is True


@pytest.mark.parametrize(
    "mutation",
    [
        {"format": "other"},
        {"framework": {"slug": "", "name": "x"}},
        {"nodes": "nope"},
        {"nodes": [{"ref_id": "1"}]},
        {"nodes": [{"ref_id": "1", "name": "a"}, {"ref_id": "1", "name": "b"}]},
        {"nodes": [{"ref_id": "2", "name": "a", "parent": "9"}]},
        {"nodes": [{"ref_id": "2", "name": "a", "parent": "3"}, {"ref_id": "3", "name": "b"}]},
    ],
)
def test_project_file_rejects_bad_input(mutation):
    with pytest.raises(ImportProblem):
        projectjson.from_dict(_project_file(**mutation)).validate()


def test_project_file_reads_from_disk(tmp_path):
    good = tmp_path / "f.json"
    good.write_text(json.dumps(_project_file()))
    assert projectjson.parse(good).slug == "acme"
    bad = tmp_path / "g.json"
    bad.write_text("{not json")
    with pytest.raises(ImportProblem, match="JSON"):
        projectjson.parse(bad)


def test_spec_validation_names_the_problem():
    spec = FrameworkSpec(
        slug="s", name="n", version="1", provider="p", nodes=[NodeSpec(ref_id="", name="x")]
    )
    with pytest.raises(ImportProblem, match="needs a reference"):
        spec.validate()
