"""
tests/test_auth_extended.py
Additional auth tests: forgot password, reset password, rate throttle branches.
"""
import pytest
import uuid
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


@pytest.mark.django_db
class TestForgotPassword:
    url = "/api/auth/forgot-password/"

    def test_valid_email_returns_200(self, api_client, owner_user):
        with pytest.MonkeyPatch().context() as mp:
            import apps.notifications.email_service as svc
            import unittest.mock as mock
            with mock.patch.object(svc, "send_mail"):
                response = api_client.post(self.url, {"email": owner_user.email})
        assert response.status_code == 200
        assert "message" in response.data

    def test_unknown_email_still_returns_200(self, api_client):
        # Should not reveal whether email exists
        response = api_client.post(self.url, {"email": "nonexistent@test.btt"})
        assert response.status_code == 200

    def test_missing_email_returns_400(self, api_client):
        response = api_client.post(self.url, {})
        assert response.status_code == 400


@pytest.mark.django_db
class TestResetPassword:
    def test_valid_token_resets_password(self, api_client, db):
        user = User.objects.create_user(
            email="reset@test.btt",
            full_name="Reset User",
            password="OldPass@123",
            role="owner",
            is_verified=True,
        )
        token = uuid.uuid4()
        user.password_reset_token = token
        user.password_reset_token_expires = timezone.now() + timedelta(hours=1)
        user.save(update_fields=["password_reset_token", "password_reset_token_expires"])

        url = f"/api/auth/reset-password/{token}/"
        response = api_client.post(url, {
            "new_password": "NewPass@999",
            "confirm_password": "NewPass@999",
        })
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.check_password("NewPass@999")

    def test_invalid_token_returns_400(self, api_client):
        url = f"/api/auth/reset-password/{uuid.uuid4()}/"
        response = api_client.post(url, {
            "new_password": "NewPass@999",
            "confirm_password": "NewPass@999",
        })
        assert response.status_code == 400

    def test_expired_token_returns_400(self, api_client, db):
        user = User.objects.create_user(
            email="expired_reset@test.btt",
            full_name="Expired",
            password="OldPass@123",
            role="owner",
        )
        token = uuid.uuid4()
        user.password_reset_token = token
        user.password_reset_token_expires = timezone.now() - timedelta(minutes=1)
        user.save(update_fields=["password_reset_token", "password_reset_token_expires"])

        url = f"/api/auth/reset-password/{token}/"
        response = api_client.post(url, {
            "new_password": "NewPass@999",
            "confirm_password": "NewPass@999",
        })
        assert response.status_code == 400

    def test_mismatched_passwords_returns_400(self, api_client, db):
        user = User.objects.create_user(
            email="mismatch@test.btt",
            full_name="Mismatch",
            password="OldPass@123",
            role="owner",
        )
        token = uuid.uuid4()
        user.password_reset_token = token
        user.password_reset_token_expires = timezone.now() + timedelta(hours=1)
        user.save(update_fields=["password_reset_token", "password_reset_token_expires"])

        url = f"/api/auth/reset-password/{token}/"
        response = api_client.post(url, {
            "new_password": "NewPass@999",
            "confirm_password": "Different@999",
        })
        assert response.status_code == 400


class TestLoginRateThrottle:
    """Unit tests for parse_rate branches."""

    def _throttle(self):
        from apps.users.views.auth_views import LoginRateThrottle
        return LoginRateThrottle()

    def test_parse_rate_none(self):
        t = self._throttle()
        assert t.parse_rate(None) == (None, None)

    def test_parse_rate_min(self):
        t = self._throttle()
        num, duration = t.parse_rate("5/15min")
        assert num == 5
        assert duration == 15 * 60

    def test_parse_rate_hour(self):
        t = self._throttle()
        num, duration = t.parse_rate("100/2hour")
        assert num == 100
        assert duration == 2 * 3600

    def test_parse_rate_day(self):
        t = self._throttle()
        num, duration = t.parse_rate("1000/1day")
        assert num == 1000
        assert duration == 86400

    def test_parse_rate_sec(self):
        t = self._throttle()
        num, duration = t.parse_rate("10/5sec")
        assert num == 10
        assert duration == 5

    def test_parse_rate_single_char_m(self):
        t = self._throttle()
        num, duration = t.parse_rate("60/m")
        assert num == 60
        assert duration == 60

    def test_parse_rate_single_char_h(self):
        t = self._throttle()
        num, duration = t.parse_rate("200/h")
        assert duration == 3600

    def test_parse_rate_single_char_d(self):
        t = self._throttle()
        num, duration = t.parse_rate("1000/d")
        assert duration == 86400
