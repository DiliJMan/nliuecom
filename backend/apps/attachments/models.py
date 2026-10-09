import hashlib
import uuid
from pathlib import PurePath

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import TimestampedModel, UUIDModel


def upload_path(instance, filename):
    """Storage name is generated, never taken from the client, so it cannot escape the folder."""
    suffix = PurePath(filename).suffix.lower()
    return f"{instance.domain_id}/{uuid.uuid4().hex}{suffix}"


def sha256_of(file) -> str:
    digest = hashlib.sha256()
    file.seek(0)
    for chunk in iter(lambda: file.read(1024 * 1024), b""):
        digest.update(chunk)
    file.seek(0)
    return digest.hexdigest()


class Attachment(UUIDModel, TimestampedModel):
    """A stored file (evidence, policy, screenshot) with a checksum taken at upload."""

    domain = models.ForeignKey(
        "domains.Domain", on_delete=models.PROTECT, related_name="attachments"
    )
    file = models.FileField(upload_to=upload_path, max_length=300)
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=150, blank=True)
    size = models.PositiveBigIntegerField()
    sha256 = models.CharField(max_length=64)
    description = models.CharField(max_length=300, blank=True)
    # Optional link to the object this file supports, by registry key and id.
    linked_object_type = models.CharField(max_length=100, blank=True)
    linked_object_id = models.CharField(max_length=64, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["linked_object_type", "linked_object_id"])]

    def __str__(self):
        return self.original_name

    def verify_integrity(self) -> bool:
        """Recompute the checksum from storage and compare with the one taken at upload."""
        with self.file.open("rb") as handle:
            return sha256_of(handle) == self.sha256


def validate_upload(uploaded) -> str:
    """Check size and extension; return a cleaned display name."""
    if uploaded.size == 0:
        raise ValidationError("The file is empty.")
    if uploaded.size > settings.ATTACHMENT_MAX_BYTES:
        limit = settings.ATTACHMENT_MAX_BYTES // (1024 * 1024)
        raise ValidationError(f"The file is larger than {limit} MB.")
    name = PurePath(uploaded.name.replace("\\", "/")).name
    name = "".join(ch for ch in name if ch.isprintable()).strip()[:255]
    if not name:
        raise ValidationError("The file needs a name.")
    if PurePath(name).suffix.lower() not in settings.ATTACHMENT_ALLOWED_EXTENSIONS:
        raise ValidationError("This file type is not accepted.")
    return name
