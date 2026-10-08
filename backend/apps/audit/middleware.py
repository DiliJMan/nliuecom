import ipaddress

from django.conf import settings

from .context import acting_as


def client_ip(request) -> str | None:
    """REMOTE_ADDR, or the first X-Forwarded-For entry when a trusted proxy is declared."""
    if request is None:
        return None
    if settings.TRUST_FORWARDED_FOR:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
        try:
            return (
                str(ipaddress.ip_address(forwarded))
                if forwarded
                else request.META.get("REMOTE_ADDR")
            )
        except ValueError:
            pass
    return request.META.get("REMOTE_ADDR")


class AuditContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        with acting_as(getattr(request, "user", None), ip=client_ip(request)):
            return self.get_response(request)
