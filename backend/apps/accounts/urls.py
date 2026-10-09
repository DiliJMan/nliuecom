from django.urls import path

from .views import CsrfView, DirectoryView, LoginView, LogoutView, MeView, PasswordChangeView

urlpatterns = [
    path("csrf/", CsrfView.as_view()),
    path("login/", LoginView.as_view()),
    path("logout/", LogoutView.as_view()),
    path("me/", MeView.as_view()),
    path("password/", PasswordChangeView.as_view()),
    path("directory/", DirectoryView.as_view()),
]
