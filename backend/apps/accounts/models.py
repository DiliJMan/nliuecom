from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models

from apps.core.models import TimestampedModel, UUIDModel


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create(self, email, password, **extra):
        if not email:
            raise ValueError("An email address is required")
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_superuser", False)
        return self._create(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra["is_superuser"] = True
        return self._create(email, password, **extra)

    def get_by_natural_key(self, username):
        return self.get(email__iexact=username)


class User(UUIDModel, TimestampedModel, AbstractBaseUser):
    """An instance user. `is_superuser` is the instance administrator flag and bypasses scoping."""

    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    objects = UserManager()

    class Meta:
        ordering = ["email"]

    def __str__(self):
        return self.email

    @property
    def display_name(self):
        full = f"{self.first_name} {self.last_name}".strip()
        return full or self.email


class UserGroup(UUIDModel, TimestampedModel):
    """A set of users that can be given roles together. Later phases map IdP groups onto these."""

    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    members = models.ManyToManyField(User, related_name="user_groups", blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
