from django.urls import path
from drf_spectacular.views import SpectacularAPIView

from .views import ObjectTypeListView

urlpatterns = [
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("object-types/", ObjectTypeListView.as_view(), name="object-types"),
]
