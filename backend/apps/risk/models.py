from django.conf import settings
from django.db import models

from apps.core.models import CustomFieldsModel, TimestampedModel, UUIDModel

from .matrix import validate_matrix


class RiskMatrix(UUIDModel, TimestampedModel):
    """Scales for likelihood and impact, and the risk level each combination gives.

    `grid[p][i]` is the index into `levels` for probability step p and impact step i, counted
    from the lowest step.
    """

    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    probability = models.JSONField(default=list)
    impact = models.JSONField(default=list)
    levels = models.JSONField(default=list)
    grid = models.JSONField(default=list)
    builtin = models.BooleanField(default=False, editable=False)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        validate_matrix(self.probability, self.impact, self.levels, self.grid)

    def save(self, *args, **kwargs):
        self.full_clean(exclude=["id"], validate_unique=False, validate_constraints=False)
        super().save(*args, **kwargs)

    def level_for(self, probability: int | None, impact: int | None) -> dict | None:
        if probability is None or impact is None:
            return None
        if not (0 <= probability < len(self.probability) and 0 <= impact < len(self.impact)):
            return None
        index = self.grid[probability][impact]
        return {"index": index, **self.levels[index]}


class RiskAssessment(UUIDModel, TimestampedModel, CustomFieldsModel):
    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        IN_PROGRESS = "in_progress", "In progress"
        IN_REVIEW = "in_review", "In review"
        DONE = "done", "Done"

    domain = models.ForeignKey(
        "domains.Domain", on_delete=models.PROTECT, related_name="risk_assessments"
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    matrix = models.ForeignKey(RiskMatrix, on_delete=models.PROTECT, related_name="assessments")
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


class RiskScenario(UUIDModel, TimestampedModel, CustomFieldsModel):
    class Treatment(models.TextChoices):
        OPEN = "open", "Not decided"
        MITIGATE = "mitigate", "Mitigate"
        ACCEPT = "accept", "Accept"
        AVOID = "avoid", "Avoid"
        TRANSFER = "transfer", "Transfer"

    risk_assessment = models.ForeignKey(
        RiskAssessment, on_delete=models.CASCADE, related_name="scenarios"
    )
    ref_id = models.CharField(max_length=100, blank=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    threats = models.TextField(blank=True)
    vulnerabilities = models.TextField(blank=True)
    existing_controls = models.TextField(blank=True)
    assets = models.ManyToManyField("assets.Asset", related_name="risk_scenarios", blank=True)
    applied_controls = models.ManyToManyField(
        "controls.AppliedControl", related_name="risk_scenarios", blank=True
    )
    # Steps on the matrix scales, counted from 0. Empty means not yet rated.
    current_probability = models.PositiveSmallIntegerField(null=True, blank=True)
    current_impact = models.PositiveSmallIntegerField(null=True, blank=True)
    residual_probability = models.PositiveSmallIntegerField(null=True, blank=True)
    residual_impact = models.PositiveSmallIntegerField(null=True, blank=True)
    treatment = models.CharField(max_length=10, choices=Treatment.choices, default=Treatment.OPEN)
    justification = models.TextField(blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["ref_id", "name"]

    def __str__(self):
        return self.name

    @property
    def domain(self):
        return self.risk_assessment.domain

    def current_level(self):
        return self.risk_assessment.matrix.level_for(self.current_probability, self.current_impact)

    def residual_level(self):
        return self.risk_assessment.matrix.level_for(
            self.residual_probability, self.residual_impact
        )
