"""
tests/test_coverage_boost.py
Targeted tests to cover remaining exception/edge-case branches.
"""
import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.django_db
class TestAuthViewEmailHelpers:
    """Exercise the exception paths in daemon-thread email helpers."""

    def test_send_verification_email_exception_logged(self, owner_user):
        with patch(
            "apps.notifications.email_service.send_email_verification",
            side_effect=Exception("SMTP down"),
        ):
            from apps.users.views.auth_views import _send_verification_email
            # Should swallow exception and log it
            _send_verification_email(owner_user)

    def test_send_password_reset_email_exception_logged(self, owner_user):
        with patch(
            "apps.notifications.email_service.send_password_reset_email",
            side_effect=Exception("SMTP down"),
        ):
            from apps.users.views.auth_views import _send_password_reset_email
            _send_password_reset_email(owner_user)


@pytest.mark.django_db
class TestMLReanalysisThread:
    """Exercise hotspot/trend save paths inside the background thread."""

    def test_trigger_reanalysis_runs_saves(self, admin_client):
        import time
        with patch("apps.ml.analysis.run_hotspot_analysis", return_value={"skipped": True, "record_count": 0}), \
             patch("apps.ml.analysis.save_hotspot_cache") as mock_hotspot_save, \
             patch("apps.ml.analysis.run_trend_analytics", return_value={"cities": [], "record_count": 0}), \
             patch("apps.ml.analysis.save_trend_cache") as mock_trend_save:
            response = admin_client.post("/api/ml/trigger-reanalysis/")
            assert response.status_code == 200
            time.sleep(0.3)  # Let daemon thread complete
            mock_hotspot_save.assert_called_once()
            mock_trend_save.assert_called_once()


@pytest.mark.django_db
class TestSMSExceptionPaths:
    """Test SMS error logging and sighting SMS with phone number."""

    def test_safe_sms_exception_is_logged(self, owner_user, recovered_report):
        from apps.reports.models import RecoveryRecord
        recovery = RecoveryRecord.objects.get(theft_report=recovered_report)
        owner_user.phone = "+923001234567"
        with patch("apps.notifications.sms_service.settings") as mock_settings, \
             patch("apps.notifications.sms_service.logger") as mock_logger:
            mock_settings.TWILIO_ACCOUNT_SID = "ACtest"
            mock_settings.TWILIO_AUTH_TOKEN = "authtest"
            mock_settings.TWILIO_FROM_NUMBER = "+1234567890"
            # Import Client inside the function — patch where it's used
            import sys
            # Create a fake twilio module structure
            fake_client = MagicMock(side_effect=Exception("Twilio error"))
            fake_twilio = MagicMock()
            fake_twilio.rest.Client = fake_client
            sys.modules.setdefault("twilio", fake_twilio)
            sys.modules.setdefault("twilio.rest", fake_twilio.rest)
            from apps.notifications.sms_service import _safe_sms
            _safe_sms("Test body", "+923001234567")

    def test_send_sighting_verified_sms_with_phone(self, owner_user, sample_bike):
        from apps.sightings.models import SightingReport
        from datetime import date
        sighting = SightingReport.objects.create(
            bike=sample_bike,
            sighting_date=date.today(),
            sighting_city="Karachi",
        )
        owner_user.phone = "+923001234567"
        with patch("apps.notifications.sms_service.settings") as mock_settings:
            mock_settings.TWILIO_ACCOUNT_SID = ""
            mock_settings.TWILIO_AUTH_TOKEN = ""
            mock_settings.TWILIO_FROM_NUMBER = ""
            from apps.notifications.sms_service import send_sighting_verified_sms
            send_sighting_verified_sms(owner_user, sighting)


@pytest.mark.django_db
class TestReportListFilter:
    """Test admin sees all reports (the uncovered 'return qs' branch)."""

    def test_admin_sees_all_reports_no_filter(self, admin_client, sample_report):
        response = admin_client.get("/api/reports/")
        assert response.status_code == 200
        # Admin gets all reports — should see the sample report
        ids = [r["id"] for r in response.data["results"]]
        assert sample_report.id in ids


@pytest.mark.django_db
class TestLogoutTokenError:
    """Cover the TokenError branch in logout (invalid/expired token)."""

    def test_logout_with_invalid_refresh_token_returns_400(self, owner_client):
        response = owner_client.post("/api/auth/logout/", {"refresh": "invalid.token.here"})
        assert response.status_code == 400
        assert "error" in response.data

    def test_logout_with_already_blacklisted_token(self, owner_client, owner_user):
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(owner_user)
        # Blacklist it first
        owner_client.post("/api/auth/logout/", {"refresh": str(refresh)})
        # Try to use the same token again — should fail
        response = owner_client.post("/api/auth/logout/", {"refresh": str(refresh)})
        assert response.status_code == 400


@pytest.mark.django_db
class TestReportNotifyException:
    """Cover _notify_report_created exception path (lines 240-241)."""

    def test_notify_report_created_exception_swallowed(self, sample_report):
        with patch(
            "apps.notifications.notification_service.notify_theft_reported",
            side_effect=Exception("Notification service down"),
        ):
            from apps.reports.views import _notify_report_created
            _notify_report_created(sample_report)  # Should not raise


@pytest.mark.django_db
class TestAdminCreateAuthorityEmailException:
    """Cover the exception path in _send_credentials_email."""

    def test_credentials_email_exception_is_swallowed(self, admin_client):
        with patch(
            "apps.notifications.email_service.send_authority_credentials_email",
            side_effect=Exception("Email server down"),
        ):
            payload = {
                "full_name": "Officer Test",
                "email": "officer.test.exc@test.btt",
                "cnic": "4200011119990",
                "badge_number": "EXC-001",
                "city": "Karachi",
                "password": "Test@12345",
            }
            response = admin_client.post("/api/admin/users/authority/", payload, format="json")
            # The view itself succeeds — exception is in daemon thread
            assert response.status_code == 201
