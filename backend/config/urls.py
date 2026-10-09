from django.urls import include, path

urlpatterns = [
    path("api/auth/", include("apps.accounts.urls")),
    path("api/", include("apps.core.urls")),
    path("api/", include("apps.domains.urls")),
    path("api/", include("apps.access.urls")),
    path("api/", include("apps.attachments.urls")),
    path("api/", include("apps.audit.urls")),
    path("api/", include("apps.frameworks.urls")),
    path("api/", include("apps.assets.urls")),
    path("api/", include("apps.controls.urls")),
    path("api/", include("apps.risk.urls")),
    path("api/", include("apps.compliance.urls")),
    path("api/", include("apps.tasks.urls")),
]
