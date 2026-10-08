from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache


def _key(email: str) -> str:
    return f"login-failures:{email.strip().lower()}"


def is_locked(email: str) -> bool:
    return cache.get(_key(email), 0) >= settings.LOGIN_MAX_FAILURES


def record_failure(email: str) -> None:
    key = _key(email)
    try:
        cache.incr(key)
    except ValueError:
        cache.set(key, 1, settings.LOGIN_LOCKOUT_SECONDS)


def clear_failures(email: str) -> None:
    cache.delete(_key(email))


class EmailBackend:
    """Case-insensitive email login that refuses locked and inactive accounts."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None
        User = get_user_model()
        try:
            user = User.objects.get(email__iexact=username)
        except User.DoesNotExist:
            # Hash anyway so response time does not reveal which addresses exist.
            User().set_password(password)
            return None
        if is_locked(username):
            return None
        if user.check_password(password) and user.is_active:
            return user
        return None

    def get_user(self, user_id):
        User = get_user_model()
        try:
            user = User.objects.get(pk=user_id)
        except (User.DoesNotExist, ValueError):
            return None
        return user if user.is_active else None
