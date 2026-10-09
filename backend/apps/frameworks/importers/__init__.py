"""Importers turn a source file into a FrameworkSpec. Register new ones in PARSERS."""

from . import iso27001, projectjson, scf

PARSERS = {
    "scf": (scf.parse, ".xlsx"),
    "iso27001": (iso27001.parse, ".pdf"),
    "project": (projectjson.parse, ".json"),
}
