from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import TimestampedModel, UUIDModel


class Framework(UUIDModel, TimestampedModel):
    """A catalogue of requirements or controls that assessments are run against.

    A framework with no domain is instance-wide: it was imported, and only an instance
    administrator manages it. A framework with a domain is a custom one, owned and editable by
    that domain (and visible to its sub-domains through ordinary roles).
    """

    slug = models.SlugField(max_length=100)
    name = models.CharField(max_length=300)
    version = models.CharField(max_length=50, blank=True)
    provider = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    domain = models.ForeignKey(
        "domains.Domain", null=True, blank=True, on_delete=models.PROTECT, related_name="frameworks"
    )
    derived_from = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="derivatives"
    )
    # Imported frameworks are read-only: their content belongs to someone else.
    locked = models.BooleanField(default=False)
    # False when the content may not be passed on (licensed or no-derivatives material).
    redistributable = models.BooleanField(default=True)
    licence_note = models.TextField(blank=True)
    attribution = models.TextField(blank=True)
    source = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["name", "version"]
        constraints = [
            models.UniqueConstraint(
                fields=["slug", "domain"], name="framework_unique_slug_per_domain"
            ),
            models.UniqueConstraint(
                fields=["slug"],
                condition=models.Q(domain__isnull=True),
                name="framework_unique_global_slug",
            ),
        ]

    def __str__(self):
        return f"{self.name} {self.version}".strip()


class RequirementNode(UUIDModel):
    """One entry in a framework: a function, domain, clause, control or requirement."""

    framework = models.ForeignKey(Framework, on_delete=models.CASCADE, related_name="nodes")
    ref_id = models.CharField(max_length=100)
    name = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="children"
    )
    order = models.PositiveIntegerField(default=0)
    # Only assessable nodes appear in a compliance assessment; the rest group them.
    assessable = models.BooleanField(default=True)
    weight = models.PositiveSmallIntegerField(default=1)
    # Source-specific extras: guidance questions, cross-references to other frameworks.
    extra = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["framework", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["framework", "ref_id"], name="node_unique_ref_per_framework"
            )
        ]

    def __str__(self):
        return f"{self.ref_id} {self.name}".strip()

    def clean(self):
        super().clean()
        if self.parent_id:
            if self.parent_id == self.pk:
                raise ValidationError({"parent": "A requirement cannot be its own parent."})
            if self.parent.framework_id != self.framework_id:
                raise ValidationError({"parent": "The parent must be in the same framework."})
            ancestor = self.parent
            while ancestor is not None:
                if ancestor.pk == self.pk:
                    raise ValidationError({"parent": "A requirement cannot move beneath itself."})
                ancestor = ancestor.parent


class RequirementMapping(UUIDModel):
    """A link between a requirement in one framework and one in another."""

    class Relationship(models.TextChoices):
        EQUAL = "equal", "Equal"
        SUBSET = "subset", "Subset of"
        SUPERSET = "superset", "Superset of"
        INTERSECTS = "intersects", "Intersects with"
        RELATED = "related", "Related"

    source = models.ForeignKey(
        RequirementNode, on_delete=models.CASCADE, related_name="mappings_out"
    )
    target = models.ForeignKey(
        RequirementNode, on_delete=models.CASCADE, related_name="mappings_in"
    )
    relationship = models.CharField(
        max_length=20, choices=Relationship.choices, default=Relationship.RELATED
    )
    # Which framework import produced the link, so it can be rebuilt after a re-import.
    origin = models.CharField(max_length=100, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["source", "target"], name="mapping_unique_pair")
        ]
