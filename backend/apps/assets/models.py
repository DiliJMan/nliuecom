from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import CustomFieldsModel, TimestampedModel, UUIDModel
from apps.core.validators import validate_web_url

OBJECTIVE = [MinValueValidator(1), MaxValueValidator(4)]


class Asset(UUIDModel, TimestampedModel, CustomFieldsModel):
    """Something worth protecting: a business process, information, a system, a site, a person."""

    class Type(models.TextChoices):
        PRIMARY = "primary", "Primary (process or information)"
        SUPPORT = "support", "Supporting (system, device, site, person)"

    domain = models.ForeignKey("domains.Domain", on_delete=models.PROTECT, related_name="assets")
    name = models.CharField(max_length=200)
    ref_id = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    type = models.CharField(max_length=10, choices=Type.choices, default=Type.SUPPORT)
    # "This asset depends on those": a payroll process depends on the HR system.
    depends_on = models.ManyToManyField(
        "self", symmetrical=False, related_name="supports", blank=True
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    business_value = models.CharField(max_length=300, blank=True)
    # Security objectives, 1 (low) to 4 (very high). Empty means not yet rated.
    confidentiality = models.PositiveSmallIntegerField(null=True, blank=True, validators=OBJECTIVE)
    integrity = models.PositiveSmallIntegerField(null=True, blank=True, validators=OBJECTIVE)
    availability = models.PositiveSmallIntegerField(null=True, blank=True, validators=OBJECTIVE)
    link = models.CharField(max_length=500, blank=True, validators=[validate_web_url])

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["domain", "name"])]

    def __str__(self):
        return self.name
