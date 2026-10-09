# Frameworks

A framework is a catalogue of requirements or controls: a standard, a regulation, a control set. A compliance assessment records, for one domain, how well each requirement is met.

## What ships with the code, and what does not

Nothing from a licensed or no-derivatives source is stored in this repository. A test fails if any PDF or spreadsheet is ever tracked, and `.gitignore` excludes them.

| Framework | How it gets into your installation | Why |
|---|---|---|
| ISO/IEC 27001:2022 | You import your own licensed PDF | The text is copyrighted by ISO/IEC and the national standards body that sold you the copy |
| Secure Controls Framework (SCF) | You import the workbook you downloaded | The SCF Council publishes it under Creative Commons terms that, on the sources checked, forbid distributing modified copies |
| NIST CSF 2.0 | Awaiting the official file (see below) | A US government publication, so it can be bundled once the official data is in hand |

Imported frameworks are locked: nobody can edit them, and the Export button is refused for licensed content. To adapt one, derive a copy owned by a domain; the copy stays under the same restriction.

## Importing

```sh
python scripts/run.py manage import_framework scf  path/to/secure-controls-framework-scf-2026-3.xlsx
python scripts/run.py manage import_framework iso27001  path/to/your-licensed-27001-2022.pdf
```

Or use the **Frameworks** page as an administrator. Add `--replace` to reload a framework, which is refused while assessments use it.

**ISO/IEC 27001:2022.** The importer reads the clauses 4 to 10 and the 93 Annex A controls. It checks its own result: Annex A must hold controls 1 to 37, 1 to 8, 1 to 14 and 1 to 34 in order, and every heading on the contents page must be found in the body. It repairs words that the PDF split across lines or with stray spaces. A copy that fails a check is refused with the reason.

**SCF.** The importer reads the sheet named like `SCF 2026.3`, builds the domains and controls, and records the references each control makes to ISO 27001:2022 and NIST CSF 2.0.

## Mappings

When two frameworks are loaded, the references recorded by the SCF become links between their requirements. They appear in the compliance workbench as **related requirements**, and an assessment can show **hints** from another assessment: results already recorded for requirements that map onto the one in front of you. A hint is a pointer. The SCF maps broadly, so read the requirement before copying a result.

Loading a framework later creates its links at once. Nothing needs re-importing.

## NIST CSF 2.0

NIST's own servers cannot be reached from the development environment, and the content is too long to type from memory without risking errors. Download the official CSF 2.0 Core from NIST's Cybersecurity and Privacy Reference Tool (JSON or Excel) and share it; the converter is written against the real file. Until then the SCF mappings that point at CSF 2.0 are stored and will link up as soon as the framework is loaded.

## Custom frameworks

Create a framework in a domain, or derive one from any loaded framework. You can add, edit and remove requirements, nest them, mark headings (not assessed), and set weights. Custom frameworks made from open content export to a project file (`nliuecom-framework/1`, JSON) that another installation can import.
