import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db
PASSWORD = "correct-horse-battery-1"


def session_client():
    client = APIClient(enforce_csrf_checks=True)
    token = client.get("/api/auth/csrf/").data["csrfToken"]
    client.credentials(HTTP_X_CSRFTOKEN=token)
    return client


def login(client, email="user@example.com", password=PASSWORD):
    return client.post("/api/auth/login/", {"email": email, "password": password}, format="json")


def test_login_requires_csrf(make_user):
    make_user()
    bare = APIClient(enforce_csrf_checks=True)
    assert login(bare).status_code == 403


def test_login_me_logout_cycle(make_user):
    make_user(first_name="Asha")
    client = session_client()
    assert client.get("/api/auth/me/").status_code == 403
    response = login(client, "USER@example.com")
    assert response.status_code == 200 and response.data["first_name"] == "Asha"
    client.credentials(HTTP_X_CSRFTOKEN=response.data["csrfToken"])
    assert "password" not in response.data
    assert client.get("/api/auth/me/").data["email"] == "user@example.com"
    assert client.post("/api/auth/logout/").status_code == 204
    assert client.get("/api/auth/me/").status_code == 403


def test_failures_look_identical_for_unknown_and_known_accounts(make_user):
    make_user()
    client = session_client()
    wrong = login(client, password="nope")
    unknown = login(client, email="ghost@example.com")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.data == unknown.data


def test_account_locks_after_repeated_failures(make_user, settings):
    settings.LOGIN_MAX_FAILURES = 3
    make_user()
    client = session_client()
    for _ in range(3):
        assert login(client, password="wrong-password").status_code == 401
    assert login(client).status_code == 401  # correct password, but locked


def test_inactive_user_cannot_sign_in(make_user):
    make_user(is_active=False)
    assert login(session_client()).status_code == 401


def test_password_change_validates_and_keeps_session(make_user):
    make_user()
    client = session_client()
    client.credentials(HTTP_X_CSRFTOKEN=login(client).data["csrfToken"])
    weak = client.post(
        "/api/auth/password/",
        {"current_password": PASSWORD, "new_password": "short"},
        format="json",
    )
    assert weak.status_code == 400
    wrong = client.post(
        "/api/auth/password/",
        {"current_password": "x", "new_password": "a-fine-new-password-3"},
        format="json",
    )
    assert wrong.status_code == 400
    ok = client.post(
        "/api/auth/password/",
        {"current_password": PASSWORD, "new_password": "a-fine-new-password-3"},
        format="json",
    )
    assert ok.status_code == 204
    assert client.get("/api/auth/me/").status_code == 200


def test_passwords_use_argon2(make_user):
    assert make_user().password.startswith("argon2")


def test_user_api_hides_and_validates_passwords(api, admin):
    client = api(admin)
    weak = client.post("/api/users/", {"email": "n@example.com", "password": "123"}, format="json")
    assert weak.status_code == 400
    ok = client.post(
        "/api/users/",
        {"email": "N@Example.com", "password": "a-long-enough-password-9"},
        format="json",
    )
    assert (
        ok.status_code == 201 and "password" not in ok.data and ok.data["email"] == "n@example.com"
    )
    dup = client.post(
        "/api/users/",
        {"email": "n@example.com", "password": "a-long-enough-password-9"},
        format="json",
    )
    assert dup.status_code == 400


def test_anonymous_requests_are_rejected():
    client = APIClient()
    for url in ("/api/domains/", "/api/users/", "/api/audit/", "/api/attachments/", "/api/schema/"):
        assert client.get(url).status_code in {401, 403}, url
