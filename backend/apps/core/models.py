import uuid

from django.db import models


class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class CustomFieldsModel(models.Model):
    """Gives a model the JSON column that holds its custom field values."""

    custom_fields = models.JSONField(default=dict, blank=True)

    class Meta:
        abstract = True
