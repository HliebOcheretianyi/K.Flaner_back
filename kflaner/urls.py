from django.urls import path

from kflaner.controllers.auth import (
    LoginController,
    LogoutController,
    MeController,
    RefreshController,
    RegisterController,
)

urlpatterns = [
    path("auth/register/", RegisterController.as_view(), name="auth-register"),
    path("auth/login/", LoginController.as_view(), name="auth-login"),
    path("auth/refresh/", RefreshController.as_view(), name="auth-refresh"),
    path("auth/logout/", LogoutController.as_view(), name="auth-logout"),
    path("auth/me/", MeController.as_view(), name="auth-me"),
]
