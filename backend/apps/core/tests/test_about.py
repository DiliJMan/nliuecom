import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_about_is_public_and_names_licence_and_source(settings):
    settings.SOURCE_URL = "https://example.org/source"
    response = APIClient().get("/api/about/")
    assert response.status_code == 200
    assert response.data["licence"] == "AGPL-3.0-or-later"
    assert response.data["source_url"] == "https://example.org/source"
