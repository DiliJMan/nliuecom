from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import CustomFieldsModel, TimestampedModel, UUIDModel


class Task(UUIDModel, TimestampedModel, CustomFieldsModel):
    class Status(models.TextChoices):
        TO_DO = "to_do", "To do"
        IN_PROGRESS = "in_progress", "In progress"
        DONE = "done", "Done"
        CANCELLED = "cancelled", "Cancelled"

    class Recurrence(models.TextChoices):
        NONE = "none", "Does not repeat"
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"
        MONTHLY = "monthly", "Monthly"
        YEARLY = "yearly", "Yearly"

    OPEN = (Status.TO_DO, Status.IN_PROGRESS)

    domain = models.ForeignKey("domains.Domain", on_delete=models.PROTECT, related_name="tasks")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tasks",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TO_DO)
    priority = models.PositiveSmallIntegerField(
        default=3, validators=[MinValueValidator(1), MaxValueValidator(4)]
    )  # 1 is most urgent
    due_date = models.DateField(null=True, blank=True)
    recurrence = models.CharField(
        max_length=10, choices=Recurrence.choices, default=Recurrence.NONE
    )
    recurrence_interval = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(365)]
    )
    reminder_days_before = models.PositiveSmallIntegerField(
        default=1, validators=[MaxValueValidator(60)]
    )
    last_reminded_on = models.DateField(null=True, blank=True, editable=False)
    completed_at = models.DateTimeField(null=True, blank=True, editable=False)
    next_task = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="+", editable=False
    )
    # The object this task is about, by registry key and id (a control, a risk scenario...).
    linked_object_type = models.CharField(max_length=100, blank=True)
    linked_object_id = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ["due_date", "priority", "title"]
        indexes = [
            models.Index(fields=["assignee", "status", "due_date"]),
            models.Index(fields=["linked_object_type", "linked_object_id"]),
        ]

    def __str__(self):
        return self.title
