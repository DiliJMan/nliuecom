from __future__ import annotations

from django.db.models import Q

from apps.frameworks.models import RequirementMapping

from .models import ComplianceAssessment, RequirementAssessment


def populate(assessment: ComplianceAssessment) -> int:
    """Create one requirement assessment for every assessable requirement in the framework."""
    nodes = assessment.framework.nodes.filter(assessable=True).values_list("pk", flat=True)
    RequirementAssessment.objects.bulk_create(
        [
            RequirementAssessment(compliance_assessment=assessment, requirement_id=pk)
            for pk in nodes
        ],
        batch_size=500,
    )
    return len(nodes)


def suggestions(target: ComplianceAssessment, source: ComplianceAssessment) -> list[dict]:
    """For each requirement not yet assessed in `target`, the results already recorded in
    `source` for requirements that map to it. These are hints for a person to weigh."""
    pending = {
        ra.requirement_id: ra for ra in target.requirement_assessments.filter(result="not_assessed")
    }
    if not pending:
        return []
    source_by_requirement = {
        ra.requirement_id: ra
        for ra in source.requirement_assessments.select_related("requirement").exclude(
            result="not_assessed"
        )
    }
    links = RequirementMapping.objects.filter(
        Q(source_id__in=pending, target_id__in=source_by_requirement)
        | Q(target_id__in=pending, source_id__in=source_by_requirement)
    ).select_related("source", "target")
    found: dict = {}
    for link in links:
        if link.source_id in pending and link.target_id in source_by_requirement:
            mine, theirs = link.source_id, link.target_id
        else:
            mine, theirs = link.target_id, link.source_id
        found.setdefault(mine, {})[theirs] = source_by_requirement[theirs]
    return [
        {
            "requirement_assessment": str(pending[mine].pk),
            "requirement": str(mine),
            "from": [
                {"ref_id": ra.requirement.ref_id, "name": ra.requirement.name, "result": ra.result}
                for ra in sorted(items.values(), key=lambda r: r.requirement.order)
            ],
        }
        for mine, items in found.items()
    ]
