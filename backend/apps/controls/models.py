from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import CustomFieldsModel, TimestampedModel, UUIDModel
from apps.core.validators import validate_web_url


class AppliedControl(UUIDModel, TimestampedModel, CustomFieldsModel):
    """A measure an organisation actually runs: a policy, a procedure, a technical safeguard."""

    class Status(models.TextChoices):
        TO_DO = "to_do", "To do"
        PLANNED = "planned", "Planned"
        IN_PROGRESS = "in_progress", "In progress"
        ACTIVE = "active", "Active"
        ON_HOLD = "on_hold", "On hold"
        DEPRECATED = "deprecated", "Deprecated"

    class Category(models.TextChoices):
        POLICY = "policy", "Policy"
        PROCESS = "process", "Process"
        TECHNICAL = "technical", "Technical"
        PHYSICAL = "physical", "Physical"
        PROCEDURE = "procedure", "Procedure"

    class Effort(models.TextChoices):
        XS = "xs", "Extra small"
        S = "s", "Small"
        M = "m", "Medium"
        L = "l", "Large"
        XL = "xl", "Extra large"

    domain = models.ForeignKey(
        "domains.Domain", on_delete=models.PROTECT, related_name="applied_controls"
    )
    name = models.CharField(max_length=200)
    ref_id = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TO_DO)
    category = models.CharField(max_length=20, choices=Category.choices, blank=True)
    priority = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(4)]
    )
    effort = models.CharField(max_length=2, choices=Effort.choices, blank=True)
    control_impact = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    eta = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    # The catalogue entry this control implements, for example an SCF control.
    reference_node = models.ForeignKey(
        "frameworks.RequirementNode",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    link = models.CharField(max_length=500, blank=True, validators=[validate_web_url])

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["domain", "status"])]

    def __str__(self):
        return self.name


class Evidence(UUIDModel, TimestampedModel, CustomFieldsModel):
    """Proof that a control works or a requirement is met: a file, a link, or both."""

    domain = models.ForeignKey("domains.Domain", on_delete=models.PROTECT, related_name="evidence")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    attachment = models.ForeignKey(
        "attachments.Attachment", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    url = models.CharField(max_length=500, blank=True, validators=[validate_web_url])
    valid_until = models.DateField(null=True, blank=True)
    applied_controls = models.ManyToManyField(AppliedControl, related_name="evidence", blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "evidence"

    def __str__(self):
        return self.name
