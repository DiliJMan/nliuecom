import pytest
from rest_framework.test import APIClient

from apps.access.models import Role, RoleAssignment
from apps.accounts.models import User, UserGroup
from apps.domains.models import Domain


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "files"


@pytest.fixture(autouse=True)
def _clear_cache():
    from django.core.cache import cache

    cache.clear()


@pytest.fixture
def make_user(db):
    def make(email="user@example.com", password="correct-horse-battery-1", **extra):
        return User.objects.create_user(email=email, password=password, **extra)

    return make


@pytest.fixture
def admin(make_user):
    return make_user("admin@example.com", is_superuser=True)


@pytest.fixture
def tree(db):
    """Global > (Europe > (France, Germany), Asia)"""
    root = Domain.objects.create(name="Global", kind="organisation")
    europe = Domain.objects.create(name="Europe", parent=root, kind="subsidiary")
    france = Domain.objects.create(name="France", parent=europe, kind="business_unit")
    germany = Domain.objects.create(name="Germany", parent=europe, kind="business_unit")
    asia = Domain.objects.create(name="Asia", parent=root, kind="subsidiary")
    return {"root": root, "europe": europe, "france": france, "germany": germany, "asia": asia}


@pytest.fixture
def grant(db):
    def make(subject, role_name, domain, recursive=True):
        role = Role.objects.get(name=role_name)
        kwargs = {"group": subject} if isinstance(subject, UserGroup) else {"user": subject}
        return RoleAssignment.objects.create(
            role=role, domain=domain, recursive=recursive, **kwargs
        )

    return make


@pytest.fixture
def api():
    def client_for(user=None):
        client = APIClient()
        if user is not None:
            client.force_authenticate(user)
        return client

    return client_for
