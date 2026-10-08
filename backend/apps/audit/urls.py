from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import AuditEventViewSet, ObjectTrailView

router = DefaultRouter()
router.register("audit", AuditEventViewSet, basename="auditevent")
urlpatterns = [
    path("audit/trail/<str:object_type>/<str:object_id>/", ObjectTrailView.as_view()),
    *router.urls,
]
