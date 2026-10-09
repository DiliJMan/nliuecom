"""The neutral shape every importer produces and the loader consumes."""

from __future__ import annotations

from dataclasses import dataclass, field


class ImportProblem(Exception):
    """The source could not be turned into a framework. The message says why."""


@dataclass
class NodeSpec:
    ref_id: str
    name: str
    description: str = ""
    parent_ref: str | None = None
    assessable: bool = True
    order: int = 0
    weight: int = 1
    extra: dict = field(default_factory=dict)


@dataclass
class FrameworkSpec:
    slug: str
    name: str
    version: str
    provider: str
    nodes: list[NodeSpec]
    description: str = ""
    licence_note: str = ""
    attribution: str = ""
    source: str = ""
    redistributable: bool = False
    notes: list[str] = field(default_factory=list)  # warnings from the parser

    def validate(self) -> None:
        seen: set[str] = set()
        for node in self.nodes:
            if not node.ref_id or not node.name:
                raise ImportProblem("Every requirement needs a reference and a name.")
            if node.ref_id in seen:
                raise ImportProblem(f"Duplicate requirement reference {node.ref_id!r}.")
            seen.add(node.ref_id)
        for node in self.nodes:
            if node.parent_ref is not None and node.parent_ref not in seen:
                raise ImportProblem(f"{node.ref_id!r} names an unknown parent {node.parent_ref!r}.")
        # Parents must come first, so loading needs one pass and cycles are impossible.
        position = {n.ref_id: i for i, n in enumerate(self.nodes)}
        for node in self.nodes:
            if node.parent_ref is not None and position[node.parent_ref] >= position[node.ref_id]:
                raise ImportProblem(
                    f"{node.ref_id!r} appears before its parent {node.parent_ref!r}."
                )
