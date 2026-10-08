from django.core.exceptions import ValidationError
from django.db import models, transaction

from apps.core.models import TimestampedModel, UUIDModel

MAX_DEPTH = 12


class DomainKind(models.TextChoices):
    ORGANISATION = "organisation", "Organisation"
    SUBSIDIARY = "subsidiary", "Subsidiary"
    BUSINESS_UNIT = "business_unit", "Business unit"
    ENTITY = "entity", "Entity"
    TEAM = "team", "Team"
    OTHER = "other", "Other"


class Domain(UUIDModel, TimestampedModel):
    """A node in the organisation tree. Objects, roles and analytics are scoped to a domain.

    `path` is a materialised path ("/<root id>/<child id>/.../<own id>/"). It makes subtree and
    ancestor lookups a single indexed query, whatever the depth.
    """

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    kind = models.CharField(max_length=20, choices=DomainKind.choices, default=DomainKind.OTHER)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="children"
    )
    path = models.CharField(max_length=512, db_index=True, editable=False, default="")
    depth = models.PositiveSmallIntegerField(default=0, editable=False)
    custom_fields = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["path"]
        constraints = [
            models.UniqueConstraint(
                fields=["parent", "name"], name="domain_unique_name_per_parent"
            ),
            models.UniqueConstraint(
                fields=["name"],
                condition=models.Q(parent__isnull=True),
                name="domain_unique_root_name",
            ),
        ]

    def __str__(self):
        return self.name

    # Tree queries -----------------------------------------------------------------------------

    def ancestor_ids(self) -> list[str]:
        """Ids on the path from the root down to, but excluding, this domain."""
        parts = [p for p in self.path.split("/") if p]
        return parts[:-1]

    def ancestors(self):
        return Domain.objects.filter(pk__in=self.ancestor_ids())

    def descendants(self, include_self: bool = False):
        qs = Domain.objects.filter(path__startswith=self.path)
        return qs if include_self else qs.exclude(pk=self.pk)

    def is_descendant_of(self, other: "Domain") -> bool:
        return self.pk != other.pk and self.path.startswith(other.path)

    # Validation and persistence ---------------------------------------------------------------

    def clean(self):
        super().clean()
        if self.parent_id:
            if self.parent_id == self.pk:
                raise ValidationError({"parent": "A domain cannot be its own parent."})
            if self._state.adding is False and self.parent.path.startswith(self.path):
                raise ValidationError({"parent": "A domain cannot move beneath its own subtree."})
            height = 0
            if self._state.adding is False:
                deepest = self.descendants().aggregate(d=models.Max("depth"))["d"]
                height = (deepest - self.depth) if deepest is not None else 0
            if self.parent.depth + 1 + height >= MAX_DEPTH:
                raise ValidationError({"parent": f"Domains can nest at most {MAX_DEPTH} levels."})

    def _compute_location(self):
        if self.parent_id:
            parent = Domain.objects.get(pk=self.parent_id)
            return f"{parent.path}{self.pk}/", parent.depth + 1
        return f"/{self.pk}/", 0

    @transaction.atomic
    def save(self, *args, **kwargs):
        self.clean()
        old_path = None
        if not self._state.adding:
            old_path = Domain.objects.filter(pk=self.pk).values_list("path", flat=True).first()
        self.path, self.depth = self._compute_location()
        super().save(*args, **kwargs)
        if old_path and old_path != self.path:
            self._relocate_subtree(old_path)

    def _relocate_subtree(self, old_path: str):
        """Rewrite descendant paths after this domain moved to a new parent."""
        shift = self.depth - old_path.strip("/").count("/")
        for child in Domain.objects.filter(path__startswith=old_path).exclude(pk=self.pk):
            child.path = self.path + child.path[len(old_path) :]
            child.depth = child.depth + shift
            models.Model.save(child, update_fields=["path", "depth"])
