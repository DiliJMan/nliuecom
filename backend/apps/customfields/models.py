from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models

from apps.core import registry
from apps.core.models import TimestampedModel, UUIDModel

KEY_VALIDATOR = RegexValidator(
    r"^[a-z][a-z0-9_]{0,63}$",
    "Use lower-case letters, digits and underscores, starting with a letter.",
)


class FieldType(models.TextChoices):
    TEXT = "text", "Text"
    NUMBER = "number", "Number"
    BOOLEAN = "boolean", "Yes or no"
    DATE = "date", "Date"
    CHOICE = "choice", "Single choice"
    MULTI_CHOICE = "multi_choice", "Multiple choice"


class CustomFieldDefinition(UUIDModel, TimestampedModel):
    """An extra attribute for one object type.

    A definition with no domain applies everywhere. One tied to a domain applies to that domain
    and everything beneath it. Values live in each object's `custom_fields` JSON column, so
    adding a field never changes the database schema.
    """

    object_type = models.CharField(max_length=100)
    key = models.CharField(max_length=64, validators=[KEY_VALIDATOR])
    label = models.CharField(max_length=150)
    help_text = models.CharField(max_length=300, blank=True)
    field_type = models.CharField(max_length=20, choices=FieldType.choices)
    required = models.BooleanField(default=False)
    choices = models.JSONField(default=list, blank=True)
    domain = models.ForeignKey(
        "domains.Domain",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="custom_field_definitions",
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["object_type", "order", "key"]
        constraints = [
            models.UniqueConstraint(
                fields=["object_type", "key", "domain"], name="customfield_unique_scoped"
            ),
            models.UniqueConstraint(
                fields=["object_type", "key"],
                condition=models.Q(domain__isnull=True),
                name="customfield_unique_global",
            ),
        ]

    def __str__(self):
        return f"{self.object_type}.{self.key}"

    def clean(self):
        super().clean()
        object_type = registry.find(self.object_type)
        if object_type is None or not object_type.supports_custom_fields:
            raise ValidationError({"object_type": "This object type does not take custom fields."})
        if self.field_type in {FieldType.CHOICE, FieldType.MULTI_CHOICE}:
            valid = (
                isinstance(self.choices, list)
                and self.choices
                and all(isinstance(c, str) and c for c in self.choices)
                and len(set(self.choices)) == len(self.choices)
            )
            if not valid:
                raise ValidationError(
                    {"choices": "Give a list of distinct, non-empty strings for choice fields."}
                )
        elif self.choices:
            raise ValidationError({"choices": "Only choice fields take a list of choices."})
        self._check_scope_conflicts()

    def _check_scope_conflicts(self):
        """A key may be defined once along any root-to-leaf path, so values never collide."""
        rivals = CustomFieldDefinition.objects.filter(
            object_type=self.object_type, key=self.key
        ).exclude(pk=self.pk)
        for rival in rivals.select_related("domain"):
            if self.domain is None or rival.domain is None:
                clash = True
            else:
                clash = self.domain.path.startswith(
                    rival.domain.path
                ) or rival.domain.path.startswith(self.domain.path)
            if clash:
                raise ValidationError(
                    {"key": f"The key '{self.key}' is already defined in an overlapping scope."}
                )

    def save(self, *args, **kwargs):
        self.full_clean(exclude=["id"], validate_unique=False, validate_constraints=False)
        super().save(*args, **kwargs)
