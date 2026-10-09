"""Reads a licensed PDF copy of ISO/IEC 27001:2022 into a framework.

The standard is copyrighted. The importer runs on the installer's own copy and writes only to
their database; nothing from the PDF is kept in this repository. It checks its own work: the
93 Annex A controls must be present and numbered without gaps, and every heading on the
contents page must be found in the body.
"""

from __future__ import annotations

import re
from pathlib import Path

from .spec import FrameworkSpec, ImportProblem, NodeSpec
from .text import build_vocabulary, join_wrapped, repair_kerning

EXPECTED_CONTROLS = {5: 37, 6: 8, 7: 14, 8: 34}  # organisational, people, physical, technological
THEMES = {
    5: "Organizational controls",
    6: "People controls",
    7: "Physical controls",
    8: "Technological controls",
}

NOTE = (
    "Imported from a licensed copy of ISO/IEC 27001:2022 supplied by the person who installed "
    "this system. The text is copyrighted. It stays inside this installation's database and "
    "cannot be exported."
)

_FURNITURE = [
    re.compile(r"^IS/ISO/IEC 27001 : 2022$"),
    re.compile(r"^ISO/IEC 27001:2022.*$"),
    re.compile(r"^[ivxl\d]{1,4}$"),  # page numbers
    re.compile(r"^(Table A\.1 \(continued\))+$"),
    re.compile(r"^Table A\.1 [—-] Information security controls$"),
    re.compile(r"^©.*$"),
]
_TOC = re.compile(r"^(\d{1,2}(?:\.\d{1,2}){0,2}) (.+?) ?\.{4,} ?\d+$")
_HEADING = re.compile(r"^(\d{1,2}(?:\.\d{1,2}){0,2}) ([A-Z].{1,150})$")
_CONTROL = re.compile(r"^([5-8]\.\d{1,2}) (.+)$")
_THEME = re.compile(r"^([5-8]) (Organizational|People|Physical|Technological) controls$")
_PARAGRAPH_START = re.compile(r"^(?:[a-z]\)|\d\)|—|NOTE\b)")


def _normalise(line: str) -> str:
    line = line.replace(" ", " ").replace("\t", " ")
    return re.sub(r" {2,}", " ", line).strip()


def _page_lines(page_text: str) -> list[str]:
    lines = (_normalise(line) for line in page_text.splitlines())
    return [ln for ln in lines if ln and not any(p.match(ln) for p in _FURNITURE)]


def _number(ref: str) -> list[int]:
    return [int(p) for p in ref.split(".")]


def _is_successor(previous: list[int], candidate: list[int]) -> bool:
    """True when `candidate` can follow `previous` in a clause outline (6.1.3 then 6.2)."""
    if candidate == previous + [1]:
        return True
    for k in range(1, len(previous) + 1):
        if (
            len(candidate) == k
            and candidate[: k - 1] == previous[: k - 1]
            and candidate[k - 1] == previous[k - 1] + 1
        ):
            return True
    return False


def _tidy(text: str, vocabulary: set[str]) -> str:
    text = re.sub(r"\s+([,;:])", r"\1", text)
    text = re.sub(r"\(\s+", "(", text)
    return repair_kerning(text, vocabulary).strip()


def _paragraphs(lines: list[str]) -> str:
    groups: list[list[str]] = []
    for line in lines:
        if not groups or _PARAGRAPH_START.match(line):
            groups.append([line])
        else:
            groups[-1].append(line)
    return "\n".join(join_wrapped(g) for g in groups)


def parse(path: str | Path) -> FrameworkSpec:
    from pypdf import PdfReader
    from pypdf.errors import PyPdfError

    try:
        reader = PdfReader(str(path))
        pages = [page.extract_text() or "" for page in reader.pages]
    except (PyPdfError, OSError, ValueError) as exc:
        raise ImportProblem(f"The file could not be read as a PDF: {exc}") from None
    return parse_pages(pages, source=f"Licensed PDF {Path(path).name}")


def parse_pages(pages: list[str], *, source: str = "") -> FrameworkSpec:
    """Turn the extracted text of each page into a framework. Separate from `parse` for testing."""
    whole = "\n".join(pages)
    if "27001" not in whole or "Annex A" not in whole:
        raise ImportProblem("This does not look like ISO/IEC 27001:2022.")

    toc = {}
    for page in pages:
        for raw in page.splitlines():
            m = _TOC.match(_normalise(raw))
            if m:
                toc[m.group(1)] = m.group(2)

    lines = [ln for page in pages for ln in _page_lines(page)]
    try:
        start = lines.index("4 Context of the organization")
        annex = lines.index("Annex A", start)
    except ValueError:
        raise ImportProblem(
            "The clause and annex headings were not found in the expected form."
        ) from None
    end = next((i for i in range(annex, len(lines)) if lines[i] == "Bibliography"), len(lines))
    vocabulary = build_vocabulary(" ".join(lines[start:end]))

    clauses = _parse_clauses(lines[start:annex], toc, vocabulary)
    controls, themes = _parse_annex(lines[annex:end], vocabulary)

    notes = []
    missing = sorted(set(k for k in toc if _number(k)[0] >= 4) - {c["ref"] for c in clauses})
    if missing:
        raise ImportProblem(
            f"Headings on the contents page were not found in the text: {', '.join(missing)}."
        )
    extra = [c["ref"] for c in clauses if c["ref"] not in toc]
    if extra:
        notes.append(f"Headings not matched against the contents page text: {', '.join(extra)}.")
    _check_controls(controls)

    nodes: list[NodeSpec] = []
    refs = {c["ref"] for c in clauses}
    for c in clauses:
        parts = c["ref"].split(".")
        has_children = any(o["ref"].startswith(c["ref"] + ".") for o in clauses)
        nodes.append(
            NodeSpec(
                ref_id=c["ref"],
                name=_tidy(c["title"], vocabulary),
                description=""
                if has_children and not c["body"]
                else _tidy(_paragraphs(c["body"]), vocabulary),
                parent_ref=".".join(parts[:-1])
                if len(parts) > 1 and ".".join(parts[:-1]) in refs
                else None,
                assessable=not has_children,
            )
        )
    nodes.append(
        NodeSpec(
            ref_id="A", name="Annex A: Information security controls reference", assessable=False
        )
    )
    for number in sorted(themes):
        nodes.append(
            NodeSpec(ref_id=f"A.{number}", name=THEMES[number], parent_ref="A", assessable=False)
        )
    for control in controls:
        nodes.append(
            NodeSpec(
                ref_id=f"A.{control['ref']}",
                name=_tidy(join_wrapped(control["title"]), vocabulary),
                description=_tidy(join_wrapped(control["text"]), vocabulary),
                parent_ref=f"A.{control['ref'].split('.')[0]}",
            )
        )
    return FrameworkSpec(
        slug="iso-27001-2022",
        name="ISO/IEC 27001:2022",
        version="2022",
        provider="ISO/IEC",
        description="Information security, cybersecurity and privacy protection: information security management systems, requirements.",
        nodes=nodes,
        licence_note=NOTE,
        attribution="ISO/IEC 27001:2022, International Organization for Standardization and International Electrotechnical Commission.",
        source=source,
        redistributable=False,
        notes=notes,
    )


def _parse_clauses(lines: list[str], toc: dict, vocabulary: set[str]) -> list[dict]:
    sections: list[dict] = []
    previous: list[int] | None = None
    for line in lines:
        m = _HEADING.match(line)
        if m and not m.group(2).endswith((".", ";", ":", ",")):
            number = _number(m.group(1))
            if (
                previous is None
                and number == [4]
                or (previous is not None and _is_successor(previous, number))
            ):
                sections.append({"ref": m.group(1), "title": m.group(2), "body": []})
                previous = number
                continue
        if sections:
            sections[-1]["body"].append(line)
    return sections


def _parse_annex(lines: list[str], vocabulary: set[str]) -> tuple[list[dict], set[int]]:
    controls: list[dict] = []
    themes: set[int] = set()
    current: dict | None = None
    for raw in lines:
        line = re.sub(r"^([5-8])\.\s+(\d)", r"\1.\2", raw)  # "7. 3" becomes "7.3"
        line = re.sub(r"([A-Za-z])Control$", r"\1 Control", line)
        collecting_title = current is not None and current["in_title"]
        if not collecting_title and (m := _THEME.match(line)):
            themes.add(int(m.group(1)))
            current = None
        elif not collecting_title and (m := _CONTROL.match(line)):
            current = {"ref": m.group(1), "title": [], "text": [], "in_title": True}
            controls.append(current)
            _title_line(current, m.group(2))
        elif current is not None:
            if current["in_title"]:
                _title_line(current, line)
            else:
                current["text"].append(line)
    return controls, themes


def _title_line(control: dict, line: str) -> None:
    if line == "Control":
        control["in_title"] = False
    elif line.endswith(" Control"):
        control["title"].append(line[: -len(" Control")])
        control["in_title"] = False
    else:
        control["title"].append(line)


def _check_controls(controls: list[dict]) -> None:
    by_theme: dict[int, list[int]] = {}
    for control in controls:
        theme, index = control["ref"].split(".")
        by_theme.setdefault(int(theme), []).append(int(index))
        if not control["title"] or not control["text"]:
            raise ImportProblem(f"Control {control['ref']} has no title or no text.")
    for theme, expected in EXPECTED_CONTROLS.items():
        found = by_theme.get(theme, [])
        if found != list(range(1, expected + 1)):
            raise ImportProblem(
                f"Annex A theme {theme} should hold controls 1 to {expected} in order; "
                f"found {len(found)}."
            )
