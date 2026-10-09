"""Small synthetic sources in the shape of the real ones. All wording here is invented."""

from __future__ import annotations

import openpyxl

SCF_HEADERS = [
    "SCF Domain",
    "SCF Control",
    "SCF #",
    "Secure Controls Framework (SCF)\nControl Description",
    "SCF Control Question",
    "Relative Control Weighting",
    "NIST CSF\nFunction Grouping",
    "ISO\n27001\n2022",
    "ISO 27002\n2022",
    "NIST\nCSF\n2.0",
]


def make_scf_workbook(
    path, *, controls_per_domain: int = 45, sheet: str = "SCF 2026.3", drop: str | None = None
):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet
    headers = [h for h in SCF_HEADERS if h != drop]
    ws.append(headers)
    domains = [("AAA", "Alpha Practices"), ("BBB", "Beta Practices"), ("CCC", "Gamma Practices")]
    for code, name in domains:
        for n in range(1, controls_per_domain + 1):
            row = {
                "SCF Domain": name,
                "SCF Control": f"{name} control {n}",
                "SCF #": f"{code}-{n:02d}",
                "Secure Controls Framework (SCF)\nControl Description": f"Mechanisms exist to do thing {n}.",
                "SCF Control Question": f"Does the organisation do thing {n}?",
                "Relative Control Weighting": 5,
                "NIST CSF\nFunction Grouping": "Protect",
                "ISO\n27001\n2022": "",
                "ISO 27002\n2022": "",
                "NIST\nCSF\n2.0": "",
            }
            if code == "AAA" and n == 1:
                row["ISO\n27001\n2022"] = "4.1\n5.1(a)\n5.1(b)\n6.1.2(c)"
                row["ISO 27002\n2022"] = "5.1\n5.4\n3.0\n8.34"
                row["NIST\nCSF\n2.0"] = "GV\nGV.OC-01"
                row["Relative Control Weighting"] = 99  # clamped
            ws.append([row.get(h) for h in headers])
        # a sub-control of the first control in each domain
        ws.append(
            [
                name,
                f"{name} sub-control",
                f"{code}-01.1",
                "Sub control text.",
                "",
                "n/a",
                "",
                "",
                "",
                "",
            ]
        )
    names = wb.create_sheet("SCF Domains & Principles")
    names.append(["#", "SCF Domain", "SCF Identifier", "Principle", "Intent"])
    for i, (code, name) in enumerate(domains, 1):
        names.append([i, name, code, "p", "i"])
    wb.save(path)


def _toc_line(ref, title, page):
    return f"{ref}  {title} {'.' * 40} {page}"


CLAUSES = [
    ("4", "Context of the organization", [], None),
    (
        "4.1",
        "Understanding things around us",
        [
            "The organization shall consider things.",
            "a) the first item;",
            "b) the second item that wraps over",
            "two lines with a split wo -",
            "rd in it.",
        ],
        None,
    ),
    ("4.2", "Needs of interested people", ["The organization shall list needs."], None),
    ("5", "Leadership", [], None),
    ("5.1", "Commitment", ["Leaders shall show commitment."], None),
    ("5.2", "Policy", ["Leaders shall set a policy.", "NOTE A policy is short."], None),
    ("6", "Planning", [], None),
    ("6.1", "Actions to address risks", [], None),
    ("6.1.1", "General", ["Plans shall be made."], None),
    ("6.1.2", "Risk assessment", ["Risks shall be assessed."], None),
    ("6.2", "Objectives", ["Objectives shall be set."], None),
    ("7", "Support", [], None),
    ("7.1", "Resources", ["Resources shall be provided."], None),
    ("8", "Operation", [], None),
    ("8.1", "Operational control", ["Operations shall be controlled."], None),
    ("9", "Performance evaluation", [], None),
    ("9.1", "Monitoring", ["Results shall be monitored."], None),
    ("10", "Improvement", [], None),
    ("10.1", "Continual improvement", ["The system shall improve."], None),
]


def make_iso_pages(
    *, drop_control: tuple[int, int] | None = None, bogus: bool = False
) -> list[str]:
    if bogus:
        return ["This is some other document.", "Nothing relevant here."]
    toc = (
        ["Contents"]
        + [
            _toc_line(ref, title, 1)
            for ref, title, _, _ in CLAUSES
            if ref != "5.2"  # the real one also misses entries
        ]
        + [
            "Annex A (normative) Controls ........ 9",
            "Bibliography ........ 12",
            "IS/ISO/IEC 27001 : 2022",
        ]
    )
    body = ["IS/ISO/IEC 27001 : 2022 example"]
    body = []
    for ref, title, text, _ in CLAUSES:
        body.append(f"{ref}\t{title}" if ref == "4" else f"{ref}  {title}")
        body.extend(text)
        if ref == "4.1":
            body.extend(
                ["1 ", "IS/ISO/IEC 27001 : 2022"]
            )  # a page break in the middle of a section
    annex = [
        "Annex A ",
        "(normative) ",
        "Information security controls reference",
        "Table A.1 — Information security controls",
    ]
    counts = {5: 37, 6: 8, 7: 14, 8: 34}
    names = {5: "Organizational", 6: "People", 7: "Physical", 8: "Technological"}
    for theme, count in counts.items():
        annex.append(f"{theme} {names[theme]} controls")
        for n in range(1, count + 1):
            if drop_control == (theme, n):
                continue
            ref = f"{theme}.{n}"
            if (theme, n) == (5, 3):
                annex += [
                    f"{ref} Handling of exam -",
                    "ple items",
                    "Control",
                    f"Text for {ref} shall be de -",
                    "fined.",
                ]
            elif (theme, n) == (7, 3):
                annex += [f"{theme}. {n} Quiet rooms Control", f"Text for {ref}."]
            elif (theme, n) == (8, 18):
                annex += [f"{ref} Spare toolsControl", f"Text for {ref}."]
            elif n % 2:
                annex += [f"{ref} Title {ref} Control", f"Text for {ref}."]
            else:
                annex += [f"{ref} Title {ref}", "Control", f"Text for {ref}."]
        annex += ["Table A.1 (continued)Table A.1 (continued)", "12", "IS/ISO/IEC 27001 : 2022"]
    annex += ["Bibliography", "[1] some reference"]
    return [
        "Cover page for ISO/IEC 27001 : 2022",
        "\n".join(toc),
        "\n".join(body),
        "\n".join(annex),
    ]
