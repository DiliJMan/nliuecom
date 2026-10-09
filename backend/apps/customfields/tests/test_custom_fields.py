import pytest
from django.core.exceptions import ValidationError

from apps.customfields.models import CustomFieldDefinition
from apps.customfields.service import CustomFieldError, validate_values

pytestmark = pytest.mark.django_db
T = "domains.domain"


def define(key="cost_centre", field_type="text", domain=None, **extra):
    return CustomFieldDefinition.objects.create(
        object_type=T, key=key, label=key, field_type=field_type, domain=domain, **extra
    )


def test_global_definition_applies_everywhere(tree):
    define()
    assert validate_values(T, tree["france"], {"cost_centre": "CC-1"}) == {"cost_centre": "CC-1"}


def test_domain_definition_applies_to_subtree_only(tree):
    define("region_code", domain=tree["europe"])
    assert validate_values(T, tree["france"], {"region_code": "FR"})
    with pytest.raises(CustomFieldError):
        validate_values(T, tree["asia"], {"region_code": "AS"})


def test_overlapping_keys_are_refused(tree):
    define("shared", domain=tree["europe"])
    with pytest.raises(ValidationError):
        define("shared", domain=tree["france"])
    with pytest.raises(ValidationError):
        define("shared")
    define("shared", domain=tree["asia"])  # a disjoint branch is fine


def test_types_are_enforced(tree):
    define("n", "number")
    define("b", "boolean")
    define("d", "date")
    define("c", "choice", choices=["low", "high"])
    define("m", "multi_choice", choices=["a", "b", "c"])
    ok = validate_values(
        T, tree["root"], {"n": 3.5, "b": True, "d": "2026-03-01", "c": "low", "m": ["c", "a", "a"]}
    )
    assert ok["m"] == ["a", "c"] and ok["d"] == "2026-03-01"
    bad = {"n": "3", "b": "yes", "d": "01/03/2026", "c": "medium", "m": ["z"]}
    with pytest.raises(CustomFieldError) as caught:
        validate_values(T, tree["root"], bad)
    assert set(caught.value.errors) == set(bad)
    with pytest.raises(CustomFieldError):
        validate_values(T, tree["root"], {"n": True})  # booleans are not numbers


def test_required_and_unknown_keys(tree):
    define("owner", required=True)
    with pytest.raises(CustomFieldError) as caught:
        validate_values(T, tree["root"], {"stray": 1})
    assert set(caught.value.errors) == {"owner", "stray"}
    assert validate_values(T, tree["root"], {}, partial=True) == {}


def test_definition_rules():
    with pytest.raises(ValidationError):
        CustomFieldDefinition.objects.create(
            object_type="accounts.usergroup", key="x", label="x", field_type="text"
        )
    with pytest.raises(ValidationError):
        define("Bad Key")
    with pytest.raises(ValidationError):
        define("empty_choice", "choice", choices=[])
    with pytest.raises(ValidationError):
        define("text_with_choices", "text", choices=["a"])


def test_values_flow_through_the_domain_api(api, admin, tree):
    define("owner", required=True)
    client = api(admin)
    created = client.post(
        "/api/domains/",
        {"name": "Spain", "parent": str(tree["europe"].pk), "custom_fields": {"owner": "Ana"}},
        format="json",
    )
    assert created.status_code == 201 and created.data["custom_fields"] == {"owner": "Ana"}
    missing = client.post(
        "/api/domains/", {"name": "Italy", "parent": str(tree["europe"].pk)}, format="json"
    )
    assert missing.status_code == 400 and "owner" in missing.data["custom_fields"]


def test_definitions_are_readable_but_writes_are_scoped(api, make_user, tree, grant):
    define("owner", domain=tree["europe"])
    reader = make_user()
    grant(reader, "Reader", tree["asia"])
    listing = api(reader).get(f"/api/custom-fields/?object_type={T}&domain={tree['france'].pk}")
    assert listing.status_code == 200 and listing.data["count"] == 1
    payload = {"object_type": T, "key": "k", "label": "K", "field_type": "text"}
    assert api(reader).post("/api/custom-fields/", payload, format="json").status_code == 403
    manager = make_user("mgr@example.com")
    grant(manager, "Domain administrator", tree["asia"])
    scoped = {**payload, "domain": str(tree["asia"].pk)}
    assert api(manager).post("/api/custom-fields/", scoped, format="json").status_code == 201
    assert (
        api(manager).post("/api/custom-fields/", payload, format="json").status_code == 403
    )  # global
