from django.conf import settings
from django.db import models

from apps.core.models import CustomFieldsModel, TimestampedModel, UUIDModel


class ComplianceAssessment(UUIDModel, TimestampedModel, CustomFieldsModel):
    """An assessment of one domain against one framework."""

    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        IN_PROGRESS = "in_progress", "In progress"
        IN_REVIEW = "in_review", "In review"
        DONE = "done", "Done"

    domain = models.ForeignKey(
        "domains.Domain", on_delete=models.PROTECT, related_name="compliance_assessments"
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    framework = models.ForeignKey(
        "frameworks.Framework", on_delete=models.PROTECT, related_name="assessments"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNED)
    version = models.CharField(max_length=50, blank=True)
    eta = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def summary(self) -> dict:
        counts = {key: 0 for key, _ in RequirementAssessment.Result.choices}
        rows = self.requirement_assessments.values("result").annotate(n=models.Count("id"))
        for row in rows:
            counts[row["result"]] = row["n"]
        total = sum(counts.values())
        applicable = total - counts["not_applicable"]
        assessed = applicable - counts["not_assessed"]
        return {
            "total": total,
            "counts": counts,
            "applicable": applicable,
            "assessed_percent": round(100 * assessed / applicable) if applicable else 0,
            "compliant_percent": round(100 * counts["compliant"] / applicable) if applicable else 0,
        }


class RequirementAssessment(UUIDModel, TimestampedModel):
    class Result(models.TextChoices):
        NOT_ASSESSED = "not_assessed", "Not assessed"
        COMPLIANT = "compliant", "Compliant"
        PARTIALLY_COMPLIANT = "partially_compliant", "Partially compliant"
        NON_COMPLIANT = "non_compliant", "Non-compliant"
        NOT_APPLICABLE = "not_applicable", "Not applicable"

    class Status(models.TextChoices):
        TO_DO = "to_do", "To do"
        IN_PROGRESS = "in_progress", "In progress"
        IN_REVIEW = "in_review", "In review"
        DONE = "done", "Done"

    compliance_assessment = models.ForeignKey(
        ComplianceAssessment, on_delete=models.CASCADE, related_name="requirement_assessments"
    )
    requirement = models.ForeignKey(
        "frameworks.RequirementNode", on_delete=models.PROTECT, related_name="assessments"
    )
    result = models.CharField(max_length=20, choices=Result.choices, default=Result.NOT_ASSESSED)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TO_DO)
    observation = models.TextField(blank=True)
    applied_controls = models.ManyToManyField(
        "controls.AppliedControl", related_name="requirement_assessments", blank=True
    )
    evidence = models.ManyToManyField(
        "controls.Evidence", related_name="requirement_assessments", blank=True
    )

    class Meta:
        ordering = ["requirement__order"]
        constraints = [
            models.UniqueConstraint(
                fields=["compliance_assessment", "requirement"], name="requirement_assessed_once"
            )
        ]

    def __str__(self):
        return f"{self.requirement.ref_id} in {self.compliance_assessment}"

    @property
    def domain(self):
        return self.compliance_assessment.domain
