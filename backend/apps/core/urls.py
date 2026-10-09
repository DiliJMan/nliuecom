from django.urls import path
from drf_spectacular.views import SpectacularAPIView

from .views import AboutView, ObjectTypeListView

urlpatterns = [
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("about/", AboutView.as_view(), name="about"),
    path("object-types/", ObjectTypeListView.as_view(), name="object-types"),
]
