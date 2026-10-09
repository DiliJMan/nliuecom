import pytest
from django.core.exceptions import ValidationError

from apps.domains.models import MAX_DEPTH, Domain

pytestmark = pytest.mark.django_db


def test_paths_and_depth(tree):
    assert tree["root"].depth == 0
    assert tree["france"].depth == 2
    assert tree["france"].path == f"/{tree['root'].pk}/{tree['europe'].pk}/{tree['france'].pk}/"


def test_descendants_and_ancestors(tree):
    names = set(tree["europe"].descendants().values_list("name", flat=True))
    assert names == {"France", "Germany"}
    assert set(tree["france"].ancestors().values_list("name", flat=True)) == {"Global", "Europe"}
    assert tree["root"].descendants(include_self=True).count() == 5
    assert tree["france"].is_descendant_of(tree["root"])
    assert not tree["root"].is_descendant_of(tree["france"])


def test_moving_a_subtree_rewrites_paths(tree):
    tree["europe"].parent = tree["asia"]
    tree["europe"].save()
    france = Domain.objects.get(pk=tree["france"].pk)
    assert france.depth == 3
    assert france.path.startswith(tree["asia"].path)
    assert france.is_descendant_of(tree["asia"])


def test_cycle_is_refused(tree):
    tree["europe"].parent = tree["france"]
    with pytest.raises(ValidationError):
        tree["europe"].save()
    tree["root"].parent = tree["root"]
    with pytest.raises(ValidationError):
        tree["root"].save()


def test_sibling_names_are_unique(tree):
    with pytest.raises(Exception):  # noqa: B017
        Domain.objects.create(name="Europe", parent=tree["root"])
    with pytest.raises(Exception):  # noqa: B017
        Domain.objects.create(name="Global")


def test_depth_limit(db):
    node = Domain.objects.create(name="d0")
    for i in range(1, MAX_DEPTH):
        node = Domain.objects.create(name=f"d{i}", parent=node)
    with pytest.raises(ValidationError):
        Domain.objects.create(name="too-deep", parent=node)


def test_domain_with_children_cannot_be_deleted(tree):
    from django.db.models import ProtectedError

    with pytest.raises(ProtectedError):
        tree["europe"].delete()
