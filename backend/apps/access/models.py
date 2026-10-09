from django.core.exceptions import ValidationError
from django.db import models

from apps.core import registry
from apps.core.models import TimestampedModel, UUIDModel


class Role(UUIDModel, TimestampedModel):
    """A named set of permission codes, each of the form "<object type>:<action>"."""

    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    permissions = models.JSONField(default=list, blank=True)
    builtin = models.BooleanField(default=False, editable=False)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if not isinstance(self.permissions, list):
            raise ValidationError({"permissions": "Permissions must be a list of codes."})
        unknown = sorted(set(self.permissions) - registry.all_permission_codes())
        if unknown:
            raise ValidationError(
                {"permissions": f"Unknown permission codes: {', '.join(unknown)}"}
            )
        self.permissions = sorted(set(self.permissions))

    def save(self, *args, **kwargs):
        self.full_clean(exclude=["id"], validate_unique=False, validate_constraints=False)
        super().save(*args, **kwargs)


class RoleAssignment(UUIDModel, TimestampedModel):
    """Grants a role to a user or a group within one domain.

    With `recursive` set, the grant also covers every domain beneath it.
    """

    user = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.CASCADE, related_name="assignments"
    )
    group = models.ForeignKey(
        "accounts.UserGroup",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="assignments")
    domain = models.ForeignKey(
        "domains.Domain", on_delete=models.CASCADE, related_name="assignments"
    )
    recursive = models.BooleanField(default=True)

    class Meta:
        ordering = ["domain__path", "role__name"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(user__isnull=False, group__isnull=True)
                    | models.Q(user__isnull=True, group__isnull=False)
                ),
                name="assignment_user_xor_group",
            ),
            models.UniqueConstraint(
                fields=["user", "role", "domain"],
                condition=models.Q(user__isnull=False),
                name="assignment_unique_user_role_domain",
            ),
            models.UniqueConstraint(
                fields=["group", "role", "domain"],
                condition=models.Q(group__isnull=False),
                name="assignment_unique_group_role_domain",
            ),
        ]

    def __str__(self):
        subject = self.user or self.group
        return f"{subject} as {self.role} on {self.domain}"
