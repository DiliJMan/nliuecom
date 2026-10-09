"""Writes a FrameworkSpec to the database and rebuilds cross-framework mappings."""

from __future__ import annotations

from django.db import transaction
from django.db.models import ProtectedError

from apps.audit import service as audit
from apps.audit.models import AuditEvent

from .importers.spec import FrameworkSpec, ImportProblem
from .models import Framework, RequirementMapping, RequirementNode


@transaction.atomic
def load(spec: FrameworkSpec, *, replace: bool = False, domain=None) -> Framework:
    """Create a framework from `spec`.

    Without a domain it is instance-wide and locked (imported content). With a domain it is a
    custom framework owned by that domain and stays editable. With `replace`, an existing
    framework with the same slug is removed first, unless assessments already use it.
    """
    spec.validate()
    existing = Framework.objects.filter(slug=spec.slug, domain=domain).first()
    if existing is not None:
        if not replace:
            raise ImportProblem(
                f"{existing} is already loaded. Re-run with replace to overwrite it."
            )
        try:
            existing.delete()
        except ProtectedError:
            raise ImportProblem(
                f"{existing} is used by compliance assessments and cannot be replaced."
            ) from None

    framework = Framework.objects.create(
        slug=spec.slug,
        name=spec.name,
        version=spec.version,
        provider=spec.provider,
        description=spec.description,
        domain=domain,
        locked=domain is None,
        redistributable=spec.redistributable,
        licence_note=spec.licence_note,
        attribution=spec.attribution,
        source=spec.source,
    )
    nodes = [
        RequirementNode(
            framework=framework,
            ref_id=n.ref_id,
            name=n.name[:500],
            description=n.description,
            order=n.order or i,
            assessable=n.assessable,
            weight=n.weight,
            extra=n.extra,
        )
        for i, n in enumerate(spec.nodes)
    ]
    by_ref = {n.ref_id: n for n in nodes}
    for node, node_spec in zip(nodes, spec.nodes, strict=True):
        if node_spec.parent_ref is not None:
            node.parent = by_ref[node_spec.parent_ref]
    RequirementNode.objects.bulk_create(nodes, batch_size=500)
    audit.record(
        AuditEvent.Action.OTHER,
        object_type="frameworks.framework",
        object_id=framework.pk,
        object_repr=str(framework),
        changes={"requirements_loaded": len(nodes), "source": spec.source},
    )
    if domain is None:
        sync_mappings()
    return framework


def sync_mappings() -> int:
    """Create RequirementMapping rows for every `extra["maps_to"]` that now resolves.

    `maps_to` is `{framework slug: [requirement references]}` on the source node. It can be
    run again whenever a framework is loaded, so mappings appear as soon as both ends exist.
    Returns how many links were added.
    """
    loaded = {
        (slug, ref_id): pk
        for slug, ref_id, pk in RequirementNode.objects.filter(
            framework__domain__isnull=True
        ).values_list("framework__slug", "ref_id", "id")
    }
    before = RequirementMapping.objects.count()
    batch: list[RequirementMapping] = []
    sources = RequirementNode.objects.filter(
        framework__domain__isnull=True, extra__has_key="maps_to"
    ).select_related("framework")
    for source in sources.iterator(chunk_size=500):
        for target_slug, refs in source.extra["maps_to"].items():
            for ref in refs:
                target_id = loaded.get((target_slug, ref))
                if target_id is not None:
                    batch.append(
                        RequirementMapping(
                            source_id=source.pk, target_id=target_id, origin=source.framework.slug
                        )
                    )
        if len(batch) >= 2000:
            RequirementMapping.objects.bulk_create(batch, ignore_conflicts=True)
            batch = []
    if batch:
        RequirementMapping.objects.bulk_create(batch, ignore_conflicts=True)
    return RequirementMapping.objects.count() - before


@transaction.atomic
def derive(framework: Framework, *, domain, name: str, slug: str) -> Framework:
    """Copy `framework` into an editable custom framework owned by `domain`."""
    copy = Framework.objects.create(
        slug=slug,
        name=name,
        version=framework.version,
        provider=framework.provider,
        description=framework.description,
        domain=domain,
        derived_from=framework,
        locked=False,
        redistributable=framework.redistributable,
        licence_note=framework.licence_note,
        attribution=framework.attribution,
        source=f"Derived from {framework}",
    )
    originals = list(framework.nodes.order_by("order"))
    clones = {
        n.pk: RequirementNode(
            framework=copy,
            ref_id=n.ref_id,
            name=n.name,
            description=n.description,
            order=n.order,
            assessable=n.assessable,
            weight=n.weight,
            extra=n.extra,
        )
        for n in originals
    }
    for n in originals:
        if n.parent_id:
            clones[n.pk].parent = clones[n.parent_id]
    RequirementNode.objects.bulk_create(list(clones.values()), batch_size=500)
    audit.record(
        AuditEvent.Action.OTHER,
        object_type="frameworks.framework",
        object_id=copy.pk,
        object_repr=str(copy),
        domain_id=domain.pk,
        changes={"requirements_copied": len(clones), "derived_from": str(framework.pk)},
    )
    return copy
