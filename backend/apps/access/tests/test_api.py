import pytest

pytestmark = pytest.mark.django_db


def names(response):
    return {row["name"] for row in response.data["results"]}


def test_user_sees_only_granted_subtree(api, make_user, tree, grant):
    user = make_user()
    grant(user, "Reader", tree["europe"])
    response = api(user).get("/api/domains/")
    assert response.status_code == 200
    assert names(response) == {"Europe", "France", "Germany"}
    assert api(user).get(f"/api/domains/{tree['asia'].pk}/").status_code == 404


def test_tree_endpoint_promotes_visible_orphans_to_roots(api, make_user, tree, grant):
    user = make_user()
    grant(user, "Reader", tree["europe"])
    roots = api(user).get("/api/domains/tree/").data
    assert [r["name"] for r in roots] == ["Europe"]
    assert {c["name"] for c in roots[0]["children"]} == {"France", "Germany"}


def test_reader_cannot_write_contributor_can(api, make_user, tree, grant):
    user = make_user()
    grant(user, "Reader", tree["europe"])
    url = f"/api/domains/{tree['france'].pk}/"
    assert api(user).patch(url, {"description": "x"}, format="json").status_code == 403
    grant(user, "Contributor", tree["france"])
    assert api(user).patch(url, {"description": "x"}, format="json").status_code == 200


def test_creating_a_domain_needs_add_on_the_parent(api, make_user, tree, grant):
    user = make_user()
    grant(user, "Manager", tree["europe"])
    ok = api(user).post(
        "/api/domains/", {"name": "Spain", "parent": str(tree["europe"].pk)}, format="json"
    )
    assert ok.status_code == 201
    outside = api(user).post(
        "/api/domains/", {"name": "Japan", "parent": str(tree["asia"].pk)}, format="json"
    )
    assert outside.status_code == 403
    top = api(user).post("/api/domains/", {"name": "Rogue"}, format="json")
    assert top.status_code == 403


def test_moving_a_domain_needs_add_on_the_new_parent(api, make_user, tree, grant):
    user = make_user()
    grant(user, "Manager", tree["europe"])
    response = api(user).patch(
        f"/api/domains/{tree['france'].pk}/", {"parent": str(tree["asia"].pk)}, format="json"
    )
    assert response.status_code == 403


def test_cycle_via_api_is_a_400(api, admin, tree):
    response = api(admin).patch(
        f"/api/domains/{tree['europe'].pk}/", {"parent": str(tree["france"].pk)}, format="json"
    )
    assert response.status_code == 400


def test_delete_of_domain_with_children_is_409(api, admin, tree):
    assert api(admin).delete(f"/api/domains/{tree['europe'].pk}/").status_code == 409


def test_users_and_roles_are_for_administrators(api, make_user, tree, grant, admin):
    user = make_user()
    grant(user, "Domain administrator", tree["root"])
    listing = api(user).get("/api/users/")
    assert listing.status_code == 200 and listing.data["results"] == []
    valid = {"email": "new@example.com", "password": "a-long-enough-password-9"}
    assert api(user).post("/api/users/", valid, format="json").status_code == 403
    assert api(user).post("/api/users/", {"email": "a@b.co"}, format="json").status_code == 403
    assert (
        api(user).post("/api/roles/", {"name": "X", "permissions": []}, format="json").status_code
        == 403
    )
    assert api(admin).get("/api/users/").status_code == 200


def test_cannot_assign_a_role_stronger_than_your_own(api, make_user, tree, grant):
    manager = make_user("m@example.com")
    target = make_user("t@example.com")
    grant(manager, "Domain administrator", tree["europe"])
    # Allowed: a role the manager fully holds.
    ok = api(manager).post(
        "/api/role-assignments/",
        {"user": str(target.pk), "role": str(_role("Reader").pk), "domain": str(tree["france"].pk)},
        format="json",
    )
    assert ok.status_code == 201, ok.data
    # Outside their scope entirely.
    out = api(manager).post(
        "/api/role-assignments/",
        {"user": str(target.pk), "role": str(_role("Reader").pk), "domain": str(tree["asia"].pk)},
        format="json",
    )
    assert out.status_code == 403
    # A lesser administrator cannot hand out the full set.
    lesser = make_user("l@example.com")
    custom = _custom_role(
        "Assigner",
        ["access.roleassignment:add", "access.roleassignment:view", "domains.domain:view"],
    )
    from apps.access.models import RoleAssignment

    RoleAssignment.objects.create(user=lesser, role=custom, domain=tree["europe"])
    over = api(lesser).post(
        "/api/role-assignments/",
        {
            "user": str(target.pk),
            "role": str(_role("Domain administrator").pk),
            "domain": str(tree["france"].pk),
        },
        format="json",
    )
    assert over.status_code == 400


def test_builtin_roles_are_protected(api, admin):
    role = _role("Reader")
    assert (
        api(admin).patch(f"/api/roles/{role.pk}/", {"permissions": []}, format="json").status_code
        == 400
    )
    assert api(admin).delete(f"/api/roles/{role.pk}/").status_code == 400


def test_assignment_needs_exactly_one_subject(api, admin, tree):
    response = api(admin).post(
        "/api/role-assignments/",
        {"role": str(_role("Reader").pk), "domain": str(tree["root"].pk)},
        format="json",
    )
    assert response.status_code == 400


def _role(name):
    from apps.access.models import Role

    return Role.objects.get(name=name)


def _custom_role(name, permissions):
    from apps.access.models import Role

    return Role.objects.create(name=name, permissions=permissions)
