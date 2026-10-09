"""The project's own framework file format, used to share and back up custom frameworks."""

from __future__ import annotations

import json
from pathlib import Path

from .spec import FrameworkSpec, ImportProblem, NodeSpec

FORMAT = "nliuecom-framework/1"
MAX_NODES = 20000


def parse(path: str | Path) -> FrameworkSpec:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ImportProblem(f"The file could not be read as JSON: {exc}") from None
    return from_dict(data)


def from_dict(data) -> FrameworkSpec:
    if not isinstance(data, dict) or data.get("format") != FORMAT:
        raise ImportProblem(f"This is not a {FORMAT} file.")
    meta, raw_nodes = data.get("framework"), data.get("nodes")
    if not isinstance(meta, dict) or not isinstance(raw_nodes, list):
        raise ImportProblem("The file needs a 'framework' object and a 'nodes' list.")
    if len(raw_nodes) > MAX_NODES:
        raise ImportProblem(f"Frameworks are limited to {MAX_NODES} requirements.")
    for key in ("slug", "name"):
        if not isinstance(meta.get(key), str) or not meta[key].strip():
            raise ImportProblem(f"framework.{key} is required.")
    nodes = []
    for i, n in enumerate(raw_nodes):
        if not isinstance(n, dict):
            raise ImportProblem(f"Requirement {i + 1} is not an object.")
        try:
            nodes.append(
                NodeSpec(
                    ref_id=str(n["ref_id"]),
                    name=str(n["name"]),
                    description=str(n.get("description", "")),
                    parent_ref=None if n.get("parent") in (None, "") else str(n["parent"]),
                    assessable=bool(n.get("assessable", True)),
                    order=int(n.get("order", i)),
                    weight=max(1, min(10, int(n.get("weight", 1)))),
                    extra=n.get("extra") if isinstance(n.get("extra"), dict) else {},
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ImportProblem(f"Requirement {i + 1} is malformed: {exc}") from None
    return FrameworkSpec(
        slug=meta["slug"].strip(),
        name=meta["name"].strip(),
        version=str(meta.get("version", "")),
        provider=str(meta.get("provider", "")),
        description=str(meta.get("description", "")),
        licence_note=str(meta.get("licence_note", "")),
        attribution=str(meta.get("attribution", "")),
        source="Project framework file",
        redistributable=bool(meta.get("redistributable", True)),
        nodes=nodes,
    )


def to_dict(framework) -> dict:
    nodes = list(framework.nodes.select_related("parent").order_by("order"))
    return {
        "format": FORMAT,
        "framework": {
            "slug": framework.slug,
            "name": framework.name,
            "version": framework.version,
            "provider": framework.provider,
            "description": framework.description,
            "licence_note": framework.licence_note,
            "attribution": framework.attribution,
            "redistributable": framework.redistributable,
        },
        "nodes": [
            {
                "ref_id": n.ref_id,
                "name": n.name,
                "description": n.description,
                "parent": n.parent.ref_id if n.parent else None,
                "assessable": n.assessable,
                "order": n.order,
                "weight": n.weight,
                "extra": n.extra,
            }
            for n in nodes
        ],
    }
