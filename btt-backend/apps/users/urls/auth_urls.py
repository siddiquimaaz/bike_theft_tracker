"""Auth URL patterns — /api/auth/"""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from apps.users.views.auth_views import (
    LoginView,
    register,
    verify_email,
    forgot_password,
    reset_password,
    logout,
)

urlpatterns = [
    path("register/", register, name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="auth-token-refresh"),
    path("verify-email/<uuid:token>/", verify_email, name="auth-verify-email"),
    path("forgot-password/", forgot_password, name="auth-forgot-password"),
    path("reset-password/<uuid:token>/", reset_password, name="auth-reset-password"),
    path("logout/", logout, name="auth-logout"),
]
