import pytest
from django.core.exceptions import ValidationError

from apps.access import policy
from apps.access.models import Role
from apps.accounts.models import UserGroup

pytestmark = pytest.mark.django_db


def test_builtin_roles_exist_and_are_valid():
    names = set(Role.objects.filter(builtin=True).values_list("name", flat=True))
    assert {"Reader", "Contributor", "Manager", "Auditor", "Domain administrator"} <= names
    reader = Role.objects.get(name="Reader")
    assert "domains.domain:view" in reader.permissions
    assert "domains.domain:change" not in reader.permissions
    assert "audit.auditevent:view" not in reader.permissions


def test_unknown_permission_codes_are_rejected():
    with pytest.raises(ValidationError):
        Role.objects.create(name="Bad", permissions=["domains.domain:explode"])


def test_recursive_grant_covers_subtree_only(make_user, tree, grant):
    user = make_user()
    grant(user, "Reader", tree["europe"])
    assert policy.has_permission(user, "domains.domain:view", tree["europe"])
    assert policy.has_permission(user, "domains.domain:view", tree["france"])
    assert not policy.has_permission(user, "domains.domain:view", tree["asia"])
    assert not policy.has_permission(user, "domains.domain:view", tree["root"])


def test_non_recursive_grant_covers_only_that_domain(make_user, tree, grant):
    user = make_user()
    grant(user, "Reader", tree["europe"], recursive=False)
    assert policy.has_permission(user, "domains.domain:view", tree["europe"])
    assert not policy.has_permission(user, "domains.domain:view", tree["france"])


def test_permission_is_per_action(make_user, tree, grant):
    user = make_user()
    grant(user, "Reader", tree["europe"])
    assert not policy.has_permission(user, "domains.domain:change", tree["france"])
    grant(user, "Contributor", tree["france"])
    assert policy.has_permission(user, "domains.domain:change", tree["france"])
    assert not policy.has_permission(user, "domains.domain:change", tree["germany"])


def test_group_grants_reach_members(make_user, tree, grant):
    user = make_user()
    group = UserGroup.objects.create(name="Analysts")
    group.members.add(user)
    grant(group, "Reader", tree["asia"])
    assert policy.has_permission(user, "domains.domain:view", tree["asia"])
    group.members.remove(user)
    assert not policy.has_permission(user, "domains.domain:view", tree["asia"])


def test_inactive_and_anonymous_users_get_nothing(make_user, tree, grant, admin):
    user = make_user()
    grant(user, "Reader", tree["root"])
    user.is_active = False
    user.save()
    assert not policy.has_permission(user, "domains.domain:view", tree["root"])
    assert policy.accessible_domain_ids(user, "domains.domain:view") == set()
    assert policy.has_permission(admin, "domains.domain:delete", tree["root"])


def test_accessible_ids(make_user, tree, grant, admin):
    user = make_user()
    grant(user, "Reader", tree["europe"])
    ids = policy.accessible_domain_ids(user, "domains.domain:view")
    assert ids == {str(tree[k].pk) for k in ("europe", "france", "germany")}
    assert policy.accessible_domain_ids(admin, "domains.domain:view") is None
