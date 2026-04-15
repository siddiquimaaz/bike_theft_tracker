"""
tests/test_notifications.py
Notification views and service functions.
"""
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def sample_notification(db, owner_user):
    from apps.notifications.models import Notification
    return Notification.objects.create(
        user=owner_user,
        type=Notification.Type.THEFT_REPORTED,
        message="Test notification",
        delivery_channel=Notification.Channel.IN_APP,
    )


@pytest.fixture
def unread_notification(db, owner_user):
    from apps.notifications.models import Notification
    return Notification.objects.create(
        user=owner_user,
        type=Notification.Type.STATUS_UPDATE,
        message="Unread notification",
        delivery_channel=Notification.Channel.IN_APP,
        is_read=False,
    )


@pytest.mark.django_db
class TestNotificationList:
    url = "/api/notifications/"

    def test_owner_can_list_notifications(self, owner_client, sample_notification):
        response = owner_client.get(self.url)
        assert response.status_code == 200
        assert "unread_count" in response.data

    def test_list_only_own_notifications(self, owner_client, authority_client, sample_notification):
        # owner_client should see their notifications
        owner_response = owner_client.get(self.url)
        assert owner_response.status_code == 200
        # authority should see empty list (notification belongs to owner)
        authority_response = authority_client.get(self.url)
        assert authority_response.status_code == 200
        assert authority_response.data["count"] == 0

    def test_unread_count_in_response(self, owner_client, unread_notification):
        response = owner_client.get(self.url)
        assert response.status_code == 200
        assert response.data["unread_count"] >= 1

    def test_unauthenticated_rejected(self, api_client):
        response = api_client.get(self.url)
        assert response.status_code == 401


@pytest.mark.django_db
class TestMarkNotificationRead:
    def test_owner_can_mark_notification_read(self, owner_client, unread_notification):
        url = f"/api/notifications/{unread_notification.id}/read/"
        response = owner_client.put(url)
        assert response.status_code == 200
        assert response.data["is_read"] is True
        unread_notification.refresh_from_db()
        assert unread_notification.is_read is True

    def test_cannot_read_others_notification(self, authority_client, sample_notification):
        url = f"/api/notifications/{sample_notification.id}/read/"
        response = authority_client.put(url)
        assert response.status_code == 404

    def test_nonexistent_notification_returns_404(self, owner_client):
        response = owner_client.put("/api/notifications/999999/read/")
        assert response.status_code == 404

    def test_unauthenticated_rejected(self, api_client, sample_notification):
        url = f"/api/notifications/{sample_notification.id}/read/"
        response = api_client.put(url)
        assert response.status_code == 401


@pytest.mark.django_db
class TestMarkAllNotificationsRead:
    url = "/api/notifications/read-all/"

    def test_owner_can_mark_all_read(self, owner_client, unread_notification):
        response = owner_client.put(self.url)
        assert response.status_code == 200
        assert "notifications marked as read" in response.data["message"]

    def test_unauthenticated_rejected(self, api_client):
        response = api_client.put(self.url)
        assert response.status_code == 401


@pytest.mark.django_db
class TestEmailService:
    """Test email service functions with mocked send_mail."""

    def test_send_email_verification(self, owner_user):
        with patch("apps.notifications.email_service.send_mail") as mock_mail:
            from apps.notifications.email_service import send_email_verification
            send_email_verification(owner_user)
            mock_mail.assert_called_once()
            args = mock_mail.call_args
            assert "Verify Your Email" in args[1]["subject"]
            assert owner_user.email in args[1]["recipient_list"]

    def test_send_email_verification_handles_exception(self, owner_user):
        with patch("apps.notifications.email_service.send_mail", side_effect=Exception("SMTP error")):
            from apps.notifications.email_service import send_email_verification
            # Should not raise — swallows exception
            send_email_verification(owner_user)

    def test_send_password_reset_email(self, owner_user):
        import uuid
        owner_user.password_reset_token = uuid.uuid4()
        owner_user.save()
        with patch("apps.notifications.email_service.send_mail") as mock_mail:
            from apps.notifications.email_service import send_password_reset_email
            send_password_reset_email(owner_user)
            mock_mail.assert_called_once()
            assert "Password Reset" in mock_mail.call_args[1]["subject"]

    def test_send_authority_credentials_email(self, authority_user):
        with patch("apps.notifications.email_service.send_mail") as mock_mail:
            from apps.notifications.email_service import send_authority_credentials_email
            send_authority_credentials_email(authority_user)
            mock_mail.assert_called_once()
            assert "Authority Account" in mock_mail.call_args[1]["subject"]

    def test_send_theft_reported_email(self, owner_user, sample_report):
        with patch("apps.notifications.email_service.send_mail") as mock_mail:
            from apps.notifications.email_service import send_theft_reported_email
            send_theft_reported_email(owner_user, sample_report)
            mock_mail.assert_called_once()
            assert "Theft Report" in mock_mail.call_args[1]["subject"]

    def test_send_status_update_email(self, owner_user, sample_report):
        with patch("apps.notifications.email_service.send_mail") as mock_mail:
            from apps.notifications.email_service import send_status_update_email
            send_status_update_email(owner_user, sample_report, "stolen")
            mock_mail.assert_called_once()
            assert "Case Update" in mock_mail.call_args[1]["subject"]

    def test_send_recovery_email(self, owner_user, recovered_report):
        from apps.reports.models import RecoveryRecord
        recovery = RecoveryRecord.objects.get(theft_report=recovered_report)
        with patch("apps.notifications.email_service.send_mail") as mock_mail:
            from apps.notifications.email_service import send_recovery_email
            send_recovery_email(owner_user, recovered_report, recovery)
            mock_mail.assert_called_once()
            assert "RECOVERED" in mock_mail.call_args[1]["subject"]

    def test_send_sighting_verified_email(self, owner_user, sample_bike):
        from apps.sightings.models import SightingReport
        from datetime import date
        sighting = SightingReport.objects.create(
            bike=sample_bike,
            sighting_date=date.today(),
            sighting_city="Karachi",
            is_verified=True,
        )
        with patch("apps.notifications.email_service.send_mail") as mock_mail:
            from apps.notifications.email_service import send_sighting_verified_email
            send_sighting_verified_email(owner_user, sighting)
            mock_mail.assert_called_once()
            assert "Sighting" in mock_mail.call_args[1]["subject"]

    def test_send_recovery_amended_email(self, owner_user, authority_user, recovered_report):
        from apps.reports.models import RecoveryRecord
        recovery = RecoveryRecord.objects.get(theft_report=recovered_report)
        with patch("apps.notifications.email_service.send_mail") as mock_mail:
            from apps.notifications.email_service import send_recovery_amended_email
            send_recovery_amended_email(owner_user, recovered_report, recovery, authority_user)
            mock_mail.assert_called_once()
            assert "Recovery Details Updated" in mock_mail.call_args[1]["subject"]


@pytest.mark.django_db
class TestNotificationService:
    """Test notification service functions."""

    def test_notify_theft_reported(self, sample_report):
        with patch("apps.notifications.email_service.send_mail"):
            from apps.notifications.notification_service import notify_theft_reported
            notify_theft_reported(sample_report)
        from apps.notifications.models import Notification
        assert Notification.objects.filter(
            user=sample_report.reported_by,
            type=Notification.Type.THEFT_REPORTED,
        ).exists()

    def test_notify_status_changed(self, sample_report):
        with patch("apps.notifications.email_service.send_mail"):
            from apps.notifications.notification_service import notify_status_changed
            notify_status_changed(sample_report, "stolen")
        from apps.notifications.models import Notification
        assert Notification.objects.filter(
            user=sample_report.reported_by,
            type=Notification.Type.STATUS_UPDATE,
        ).exists()

    def test_notify_bike_recovered(self, recovered_report):
        from apps.reports.models import RecoveryRecord
        recovery = RecoveryRecord.objects.get(theft_report=recovered_report)
        with patch("apps.notifications.email_service.send_mail"), \
             patch("apps.notifications.sms_service._safe_sms"):
            from apps.notifications.notification_service import notify_bike_recovered
            notify_bike_recovered(recovered_report, recovery)
        from apps.notifications.models import Notification
        assert Notification.objects.filter(
            type=Notification.Type.RECOVERY,
        ).exists()

    def test_notify_recovery_amended(self, recovered_report, authority_user):
        from apps.reports.models import RecoveryRecord
        recovery = RecoveryRecord.objects.get(theft_report=recovered_report)
        with patch("apps.notifications.email_service.send_mail"):
            from apps.notifications.notification_service import notify_recovery_amended
            notify_recovery_amended(recovered_report, recovery, authority_user)

    def test_notify_sighting_submitted_with_sighter(self, community_user, sample_bike):
        from apps.sightings.models import SightingReport
        from datetime import date
        sighting = SightingReport.objects.create(
            sighter=community_user,
            sighting_date=date.today(),
            sighting_city="Karachi",
        )
        from apps.notifications.notification_service import notify_sighting_submitted
        notify_sighting_submitted(sighting)
        from apps.notifications.models import Notification
        assert Notification.objects.filter(user=community_user).exists()

    def test_notify_sighting_submitted_no_sighter(self, sample_bike):
        from apps.sightings.models import SightingReport
        from datetime import date
        sighting = SightingReport.objects.create(
            sighting_date=date.today(),
            sighting_city="Karachi",
        )
        from apps.notifications.notification_service import notify_sighting_submitted
        # Should not raise even with no sighter
        notify_sighting_submitted(sighting)

    def test_notify_sighting_verified(self, authority_user, sample_bike, owner_user):
        from apps.sightings.models import SightingReport
        from datetime import date
        sighting = SightingReport.objects.create(
            bike=sample_bike,
            sighting_date=date.today(),
            sighting_city="Karachi",
            is_verified=True,
            verified_by=authority_user,
        )
        with patch("apps.notifications.email_service.send_mail"), \
             patch("apps.notifications.sms_service._safe_sms"):
            from apps.notifications.notification_service import notify_sighting_verified
            notify_sighting_verified(sighting)
        from apps.notifications.models import Notification
        assert Notification.objects.filter(
            user=owner_user,
            type=Notification.Type.SIGHTING_MATCHED,
        ).exists()

    def test_notify_sighting_verified_no_bike(self):
        from apps.sightings.models import SightingReport
        from datetime import date
        sighting = SightingReport(
            sighting_date=date.today(),
            sighting_city="Karachi",
        )
        # bike is None — should return early
        from apps.notifications.notification_service import notify_sighting_verified
        notify_sighting_verified(sighting)  # should not raise


@pytest.mark.django_db
class TestSMSService:
    """Test SMS service functions."""

    def test_send_recovery_sms_no_phone(self, owner_user, recovered_report):
        from apps.reports.models import RecoveryRecord
        recovery = RecoveryRecord.objects.get(theft_report=recovered_report)
        owner_user.phone = None
        # No phone — should return early without calling Twilio at all
        from apps.notifications.sms_service import send_recovery_sms
        send_recovery_sms(owner_user, recovered_report, recovery)
        # No assertion needed — just checking no exception raised

    def test_send_recovery_sms_with_phone(self, owner_user, recovered_report):
        from apps.reports.models import RecoveryRecord
        recovery = RecoveryRecord.objects.get(theft_report=recovered_report)
        owner_user.phone = "+923001234567"
        with patch("twilio.rest.Client") as mock_client:
            mock_messages = MagicMock()
            mock_client.return_value.messages = mock_messages
            mock_messages.create.return_value.sid = "SMTEST123"
            from apps.notifications.sms_service import send_recovery_sms
            send_recovery_sms(owner_user, recovered_report, recovery)

    def test_send_sighting_verified_sms_no_phone(self, owner_user, sample_bike):
        from apps.sightings.models import SightingReport
        from datetime import date
        sighting = SightingReport.objects.create(
            bike=sample_bike,
            sighting_date=date.today(),
            sighting_city="Karachi",
        )
        owner_user.phone = None
        from apps.notifications.sms_service import send_sighting_verified_sms
        send_sighting_verified_sms(owner_user, sighting)
        # Should return early without error

    def test_sms_skipped_when_no_twilio_credentials(self):
        with patch("apps.notifications.sms_service.settings") as mock_settings:
            mock_settings.TWILIO_ACCOUNT_SID = ""
            mock_settings.TWILIO_AUTH_TOKEN = ""
            mock_settings.TWILIO_FROM_NUMBER = ""
            from apps.notifications.sms_service import _safe_sms
            _safe_sms("test body", "+923001234567")  # should not raise

    def test_safe_sms_no_phone_number(self):
        with patch("apps.notifications.sms_service.settings") as mock_settings:
            mock_settings.TWILIO_ACCOUNT_SID = "ACtest"
            mock_settings.TWILIO_AUTH_TOKEN = "authtest"
            mock_settings.TWILIO_FROM_NUMBER = "+1234567890"
            from apps.notifications.sms_service import _safe_sms
            _safe_sms("test body", "")  # empty number — should log and return
