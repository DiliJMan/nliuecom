from django.urls import include, path

urlpatterns = [
    path("api/auth/", include("apps.accounts.urls")),
    path("api/", include("apps.core.urls")),
    path("api/", include("apps.domains.urls")),
    path("api/", include("apps.access.urls")),
    path("api/", include("apps.attachments.urls")),
    path("api/", include("apps.audit.urls")),
]
