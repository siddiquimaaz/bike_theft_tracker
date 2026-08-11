"""
apps/users/views/auth_views.py
Authentication endpoints — public and semi-public.
"""
import re
import uuid
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.validators import validate_email as django_validate_email
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from datetime import timedelta
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.common.api import error_response
from apps.common.background import deferred_task, run_in_background
from apps.users.serializers import (
    UserRegistrationSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
)

CNIC_DIGITS_PATTERN = re.compile(r"^\d{13}$")

User = get_user_model()


class LoginRateThrottle(AnonRateThrottle):
    scope = "login"

    def parse_rate(self, rate):
        """Parse rates like '5/15min', '5/min', '10/hour', '30/15min'."""
        if rate is None:
            return (None, None)
        num, period = rate.split("/")
        num_requests = int(num)

        # Standard single-unit shorthand: s, m, h, d
        _standard = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        if period in _standard:
            return (num_requests, _standard[period])

        # Extended unit names with optional numeric prefix, e.g. "15min", "min", "2hour"
        _units = [("min", 60), ("hour", 3600), ("day", 86400), ("sec", 1)]
        for suffix, multiplier in _units:
            if period.endswith(suffix):
                prefix = period[: -len(suffix)]
                # prefix is either a number ("15") or empty string (meaning 1)
                count = int(prefix) if prefix else 1
                return (num_requests, count * multiplier)

        raise ValueError(f"Unrecognised throttle rate period: '{period}'. "
                         f"Use formats like '5/min', '5/15min', '10/hour'.")



class BTTTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Extend the JWT payload with role, full_name and email so the
    React frontend can read the user's role directly from the token."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"]      = user.role
        token["email"]     = user.email
        token["full_name"] = user.full_name
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        # Block login for unverified accounts so users can't obtain JWTs
        # that will immediately fail RBAC checks on owner/authority/admin endpoints.
        if not getattr(self.user, "is_verified", False):
            from rest_framework.exceptions import AuthenticationFailed
            raise AuthenticationFailed(
                "Email verification required before logging in."
            )
        # Also return user info alongside tokens so the frontend
        # can populate its auth context without decoding the JWT.
        data["user"] = {
            "id":        self.user.id,
            "email":     self.user.email,
            "role":      self.user.role,
            "full_name": self.user.full_name,
            "city":      self.user.city,
        }
        return data


def _throttle_classes(*classes):
    """Return throttle classes list, or empty list when DISABLE_THROTTLE=True."""
    from django.conf import settings as django_settings
    return [] if getattr(django_settings, "DISABLE_THROTTLE", False) else list(classes)


class LoginView(TokenObtainPairView):
    serializer_class = BTTTokenObtainPairSerializer
    throttle_classes = _throttle_classes(LoginRateThrottle)
    permission_classes = [AllowAny]


# ─── Registration ─────────────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    """
    POST /api/auth/register/
    Register a new Owner or Community Reporter.
    Sends email verification link. Login blocked until verified.
    """
    serializer = UserRegistrationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    user.email_verification_token = uuid.uuid4()
    user.email_verification_token_expires = timezone.now() + timedelta(hours=24)
    user.save(update_fields=["email_verification_token", "email_verification_token_expires"])

    # Send verification email in background — non-blocking
    run_in_background(_send_verification_email, user)

    payload = {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "message": "Registration successful. Please verify your email before logging in.",
    }
    if settings.LOCAL_DEV_MODE:
        payload["verification_token"] = str(user.email_verification_token)
        payload["verification_url"] = f"/api/auth/verify-email/{user.email_verification_token}/"
    return Response(payload, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([AllowAny])
def verify_email(request, token):
    """
    POST /api/auth/verify-email/{token}/
    Verifies user's email using UUID token sent at registration.
    """
    try:
        user = User.objects.get(
            email_verification_token=token,
            is_verified=False,
            email_verification_token_expires__gt=timezone.now(),
        )
    except User.DoesNotExist:
        return Response(
            {"error": "Invalid or already used verification token."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user.is_verified = True
    user.email_verification_token = uuid.uuid4()  # Rotate — invalidate reuse
    user.email_verification_token_expires = None
    user.save(update_fields=["is_verified", "email_verification_token", "email_verification_token_expires"])

    return Response({"message": "Email verified successfully. You may now log in."})


# ─── Password Reset ───────────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([AllowAny])
def forgot_password(request):
    """
    POST /api/auth/forgot-password/
    Sends password reset link to registered email. Always returns 200
    (prevents email enumeration).
    """
    serializer = PasswordResetRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        user = User.objects.get(email=serializer.validated_data["email"], is_active=True)
        user.password_reset_token = uuid.uuid4()
        user.password_reset_token_expires = timezone.now() + timedelta(hours=1)
        user.save(update_fields=["password_reset_token", "password_reset_token_expires"])
        run_in_background(_send_password_reset_email, user)
    except User.DoesNotExist:
        pass  # Intentional — don't reveal whether email exists

    return Response(
        {"message": "If that email is registered, a reset link has been sent."}
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def reset_password(request, token):
    """
    POST /api/auth/reset-password/{token}/
    Sets new password. Token expires in 1 hour and is single-use.
    """
    try:
        user = User.objects.get(
            password_reset_token=token,
            password_reset_token_expires__gt=timezone.now(),
            is_active=True,
        )
    except User.DoesNotExist:
        return Response(
            {"error": "Invalid or expired password reset token."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    serializer = PasswordResetConfirmSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    user.set_password(serializer.validated_data["new_password"])
    user.password_reset_token = None
    user.password_reset_token_expires = None
    user.save(update_fields=["password", "password_reset_token", "password_reset_token_expires"])

    return Response({"message": "Password reset successfully. You may now log in."})


# ─── Logout ───────────────────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    POST /api/auth/logout/
    Blacklists refresh token. Access token expires naturally after 15 minutes.
    """
    refresh_token = request.data.get("refresh")
    if not refresh_token:
        return error_response("refresh token is required.", status.HTTP_400_BAD_REQUEST)
    try:
        token = RefreshToken(refresh_token)
        token.blacklist()
    except TokenError as exc:
        return error_response(str(exc), status.HTTP_400_BAD_REQUEST)

    return Response({"message": "Logged out successfully."})


# ─── Pre-submit availability checks ───────────────────────────────────────────
#
# Lightweight GET endpoints used by the register form to validate email and
# CNIC inline (onBlur) before the user hits submit. They are cheap — one indexed
# `.exists()` query each — and do not reveal any user data.
#
# Security notes:
#   - AnonRateThrottle('anon_check') caps enumeration attempts per IP.
#   - Response shape is intentionally boolean so we do NOT leak whether an
#     email/CNIC belongs to an owner vs. an authority, only that it is taken.
#   - Input normalisation mirrors the registration serializer (lowercasing
#     email, stripping CNIC hyphens) so the precheck matches the real check.


class AvailabilityCheckThrottle(AnonRateThrottle):
    scope = "availability_check"


@api_view(["GET"])
@permission_classes([AllowAny])
@throttle_classes(_throttle_classes(AvailabilityCheckThrottle))
def check_email(request):
    """
    GET /api/auth/check-email/?email=you@example.com
    Returns {available, valid_format, reason}.
    """
    raw = (request.query_params.get("email") or "").strip().lower()
    if not raw:
        return Response(
            {"available": False, "valid_format": False, "reason": "Email is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        django_validate_email(raw)
    except DjangoValidationError:
        return Response(
            {"available": False, "valid_format": False, "reason": "Invalid email format."}
        )

    taken = User.objects.filter(email__iexact=raw).exists()
    return Response({
        "available": not taken,
        "valid_format": True,
        "reason": "Email already registered." if taken else "Available.",
    })


@api_view(["GET"])
@permission_classes([AllowAny])
@throttle_classes(_throttle_classes(AvailabilityCheckThrottle))
def check_cnic(request):
    """
    GET /api/auth/check-cnic/?cnic=4200012345678
    Returns {available, valid_format, reason}.
    Hyphens and spaces are stripped before validation so the client may send
    either '42000-1234567-8' or '4200012345678'.
    """
    raw = (request.query_params.get("cnic") or "").replace("-", "").replace(" ", "")
    if not raw:
        return Response(
            {"available": False, "valid_format": False, "reason": "CNIC is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not CNIC_DIGITS_PATTERN.match(raw):
        return Response(
            {"available": False, "valid_format": False, "reason": "CNIC must be exactly 13 digits."}
        )

    taken = User.objects.filter(cnic=raw).exists()
    return Response({
        "available": not taken,
        "valid_format": True,
        "reason": "CNIC already registered." if taken else "Available.",
    })


# ─── Email helpers ────────────────────────────────────────────────────────────

_send_verification_email = deferred_task(
    "apps.notifications.email_service", "send_email_verification",
    "Failed to send verification email: %s",
)

_send_password_reset_email = deferred_task(
    "apps.notifications.email_service", "send_password_reset_email",
    "Failed to send password reset email: %s",
)
