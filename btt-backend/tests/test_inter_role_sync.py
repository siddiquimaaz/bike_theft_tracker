"""
tests/test_inter_role_sync.py
────────────────────────────
Comprehensive inter-role synchronisation tests.

Every test exercises at least two roles to verify that:
  - Data written by one role is (or is NOT) visible to another
  - Status transitions by authority surface correctly to the owner
  - City-scoped access is enforced end-to-end
  - Notification service functions produce the right records per role
  - Community users are correctly isolated from report data

Notification assertions call service functions directly — no daemon-thread
timing dependencies.
"""
import pytest
from datetime import date


# ══════════════════════════════════════════════════════════════════════════════
# 1. BIKE STATUS VISIBILITY ACROSS ROLES
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestBikeStatusAcrossRoles:
    """Stolen-bike status and endpoint access per role."""

    def test_owner_sees_own_bike_in_list(self, owner_client, sample_bike):
        resp = owner_client.get("/api/bikes/")
        assert resp.status_code == 200
        ids = [b["id"] for b in resp.data["results"]]
        assert sample_bike.id in ids

    def test_authority_cannot_access_bike_list(self, authority_client):
        resp = authority_client.get("/api/bikes/")
        assert resp.status_code == 403

    def test_community_cannot_access_bike_list(self, community_client):
        resp = community_client.get("/api/bikes/")
        assert resp.status_code == 403

    def test_authority_sees_stolen_bike_in_stolen_endpoint(
        self, authority_client, sample_bike, sample_report
    ):
        resp = authority_client.get("/api/bikes/stolen/")
        assert resp.status_code == 200
        ids = [b["id"] for b in resp.data["results"]]
        assert sample_bike.id in ids

    def test_admin_sees_stolen_bike_in_stolen_endpoint(
        self, admin_client, sample_bike, sample_report
    ):
        resp = admin_client.get("/api/bikes/stolen/")
        assert resp.status_code == 200
        ids = [b["id"] for b in resp.data["results"]]
        assert sample_bike.id in ids

    def test_owner_cannot_access_stolen_endpoint(self, owner_client):
        resp = owner_client.get("/api/bikes/stolen/")
        assert resp.status_code == 403

    def test_community_cannot_access_stolen_endpoint(self, community_client):
        resp = community_client.get("/api/bikes/stolen/")
        assert resp.status_code == 403

    def test_public_search_marks_bike_stolen(self, api_client, sample_bike, sample_report):
        resp = api_client.get(f"/api/search/bike/?q={sample_bike.engine_number}")
        assert resp.status_code == 200
        results = resp.data["results"]
        assert len(results) >= 1
        assert results[0]["status"] == "REPORTED STOLEN"

    def test_public_search_response_has_no_owner_or_email_key(
        self, api_client, sample_bike, sample_report
    ):
        resp = api_client.get(f"/api/search/bike/?q={sample_bike.engine_number}")
        assert resp.status_code == 200
        result = resp.data["results"][0]
        assert "owner" not in result
        assert "email" not in result

    def test_public_search_non_stolen_bike_shows_correct_status(
        self, api_client, sample_bike
    ):
        resp = api_client.get(f"/api/search/bike/?q={sample_bike.engine_number}")
        assert resp.status_code == 200
        results = resp.data["results"]
        assert results[0]["status"] != "REPORTED STOLEN"

    def test_city_count_reflects_active_new_case_report(self, api_client, sample_report):
        resp = api_client.get("/api/search/city/Karachi/")
        assert resp.status_code == 200
        assert resp.data["active_theft_reports"] >= 1


# ══════════════════════════════════════════════════════════════════════════════
# 2. REPORT LIFECYCLE — MULTI-ROLE FLOW
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestReportLifecycle:
    """Full lifecycle: owner files → authority progresses → owner closes."""

    def test_owner_files_report_authority_sees_it(
        self, owner_client, authority_client, sample_bike
    ):
        payload = {
            "bike": sample_bike.id,
            "theft_date": str(date.today()),
            "theft_city": "Karachi",
        }
        create_resp = owner_client.post("/api/reports/", payload, format="json")
        assert create_resp.status_code == 201
        ref = create_resp.data["reference_number"]

        list_resp = authority_client.get("/api/reports/")
        assert list_resp.status_code == 200
        refs = [r["reference_number"] for r in list_resp.data["results"]]
        assert ref in refs

    def test_authority_transitions_new_case_to_under_review(
        self, authority_client, sample_report
    ):
        resp = authority_client.put(
            f"/api/reports/{sample_report.id}/status/",
            {"status": "under_review"}, format="json"
        )
        assert resp.status_code == 200
        assert resp.data["old_status"] == "new_case"
        assert resp.data["new_status"] == "under_review"

    def test_authority_chains_under_review_to_active_investigation(
        self, authority_client, sample_report
    ):
        authority_client.put(
            f"/api/reports/{sample_report.id}/status/",
            {"status": "under_review"}, format="json"
        )
        resp = authority_client.put(
            f"/api/reports/{sample_report.id}/status/",
            {"status": "active_investigation"}, format="json"
        )
        assert resp.status_code == 200
        assert resp.data["old_status"] == "under_review"
        assert resp.data["new_status"] == "active_investigation"

    def test_owner_sees_updated_status_after_authority_transition(
        self, owner_client, authority_client, sample_report
    ):
        authority_client.put(
            f"/api/reports/{sample_report.id}/status/",
            {"status": "under_review"}, format="json"
        )
        detail_resp = owner_client.get(f"/api/reports/{sample_report.id}/")
        assert detail_resp.status_code == 200
        assert detail_resp.data["status"] == "under_review"

    def test_owner_cannot_change_report_status(self, owner_client, sample_report):
        resp = owner_client.put(
            f"/api/reports/{sample_report.id}/status/",
            {"status": "under_review"}, format="json"
        )
        assert resp.status_code == 403

    def test_community_gets_404_on_report_detail(self, community_client, sample_report):
        resp = community_client.get(f"/api/reports/{sample_report.id}/")
        assert resp.status_code == 404

    def test_community_list_returns_200_with_empty_results(
        self, community_client, sample_report
    ):
        resp = community_client.get("/api/reports/")
        assert resp.status_code == 200
        assert len(resp.data["results"]) == 0

    def test_community_cannot_post_report(self, community_client, sample_bike):
        payload = {
            "bike": sample_bike.id,
            "theft_date": str(date.today()),
            "theft_city": "Karachi",
        }
        resp = community_client.post("/api/reports/", payload, format="json")
        assert resp.status_code == 403

    def test_owner_cannot_see_another_owners_report(
        self, owner_client, owner_user_2, db
    ):
        from apps.bikes.models import Bike
        from apps.reports.models import TheftReport

        bike2 = Bike.objects.create(
            owner=owner_user_2,
            make="Yamaha", model="YBR 125", year=2021,
            engine_number="SYNC-OWN2-ENG-001",
            chassis_number="SYNC-OWN2-CHS-001",
        )
        report2 = TheftReport.objects.create(
            bike=bike2,
            reported_by=owner_user_2,
            theft_date=date.today(),
            theft_city="Karachi",
        )
        resp = owner_client.get(f"/api/reports/{report2.id}/")
        assert resp.status_code == 404

    def test_admin_can_see_all_reports(self, admin_client, sample_report):
        resp = admin_client.get("/api/reports/")
        assert resp.status_code == 200
        ids = [r["id"] for r in resp.data["results"]]
        assert sample_report.id in ids

    def test_admin_soft_delete_object_still_exists_with_deleted_at(
        self, admin_client, sample_report
    ):
        from apps.reports.models import TheftReport

        resp = admin_client.delete(f"/api/reports/{sample_report.id}/")
        assert resp.status_code == 204

        try:
            sample_report.refresh_from_db()
        except TheftReport.DoesNotExist:
            pytest.fail("soft delete must keep the DB row — DoesNotExist raised")

        assert sample_report.deleted_at is not None


# ══════════════════════════════════════════════════════════════════════════════
# 3. CITY-SCOPED AUTHORITY ACCESS
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestCityScopedAuthorityAccess:
    """Authority can only work within their assigned city."""

    def test_lahore_authority_cannot_see_karachi_report(
        self, authority_client_lahore, sample_report
    ):
        resp = authority_client_lahore.get("/api/reports/")
        assert resp.status_code == 200
        ids = [r["id"] for r in resp.data["results"]]
        assert sample_report.id not in ids

    def test_lahore_authority_gets_404_transitioning_karachi_report(
        self, authority_client_lahore, sample_report
    ):
        resp = authority_client_lahore.put(
            f"/api/reports/{sample_report.id}/status/",
            {"status": "under_review"}, format="json"
        )
        assert resp.status_code == 404

    def test_karachi_authority_cannot_verify_lahore_sighting(
        self, authority_client
    ):
        from apps.sightings.models import SightingReport

        sighting = SightingReport.objects.create(
            sighting_date=date.today(),
            sighting_city="Lahore",
            raw_engine_number="CROSS-CITY-ENG-001",
        )
        resp = authority_client.put(
            f"/api/sightings/{sighting.id}/verify/",
            {"bike_id": 999}, format="json"
        )
        assert resp.status_code == 403
        assert "assigned city" in resp.data.get("error", "")

    def test_karachi_authority_can_verify_karachi_sighting(
        self, authority_client, sample_bike
    ):
        from apps.sightings.models import SightingReport

        sighting = SightingReport.objects.create(
            sighting_date=date.today(),
            sighting_city="Karachi",
            raw_engine_number="SAME-CITY-ENG-001",
        )
        resp = authority_client.put(
            f"/api/sightings/{sighting.id}/verify/",
            {"bike_id": sample_bike.id}, format="json"
        )
        assert resp.status_code == 200
        assert resp.data["is_verified"] is True

    def test_authority_with_empty_city_gets_200_with_zero_count(self, db):
        from django.contrib.auth import get_user_model
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import RefreshToken

        User = get_user_model()
        no_city_auth = User.objects.create_user(
            full_name="No City Auth",
            email="nocity@sync.btt",
            role="authority",
            badge_number="NOCITY-SYNC-001",
            cnic="4200077777771",
            password="Test@12345",
            is_verified=True,
            is_active=True,
            city="",
        )
        client = APIClient()
        refresh = RefreshToken.for_user(no_city_auth)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")

        resp = client.get("/api/reports/")
        assert resp.status_code == 200
        assert resp.data["count"] == 0


# ══════════════════════════════════════════════════════════════════════════════
# 4. SIGHTING ROLE VISIBILITY
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestSightingRoleVisibility:
    """Sighting list and detail access scoped correctly per role."""

    def test_community_sees_only_own_sightings(
        self, community_client, community_user, owner_user
    ):
        from apps.sightings.models import SightingReport

        own = SightingReport.objects.create(
            sighter=community_user,
            raw_engine_number="OWN-SIGHT-SYNC-001",
            sighting_date=date.today(),
            sighting_city="Karachi",
        )
        other = SightingReport.objects.create(
            sighter=owner_user,
            raw_engine_number="OTHER-SIGHT-SYNC-001",
            sighting_date=date.today(),
            sighting_city="Lahore",
        )
        resp = community_client.get("/api/sightings/")
        assert resp.status_code == 200
        ids = [s["id"] for s in resp.data["results"]]
        assert own.id in ids
        assert other.id not in ids

    def test_authority_sees_all_unverified_sightings(
        self, authority_client, community_user
    ):
        from apps.sightings.models import SightingReport

        sighting = SightingReport.objects.create(
            sighter=community_user,
            raw_engine_number="AUTH-VIEW-SYNC-001",
            sighting_date=date.today(),
            sighting_city="Karachi",
        )
        resp = authority_client.get("/api/sightings/")
        assert resp.status_code == 200
        ids = [s["id"] for s in resp.data["results"]]
        assert sighting.id in ids

    def test_authority_does_not_see_verified_sightings_in_queue(
        self, authority_client, community_user, sample_bike, authority_user
    ):
        from apps.sightings.models import SightingReport

        verified = SightingReport.objects.create(
            sighter=community_user,
            raw_engine_number="VERIFIED-SYNC-001",
            sighting_date=date.today(),
            sighting_city="Karachi",
            is_verified=True,
            verified_by=authority_user,
            bike=sample_bike,
        )
        resp = authority_client.get("/api/sightings/")
        assert resp.status_code == 200
        ids = [s["id"] for s in resp.data["results"]]
        assert verified.id not in ids

    def test_owner_gets_404_on_another_users_sighting_detail(
        self, owner_client, community_user
    ):
        from apps.sightings.models import SightingReport

        other_sighting = SightingReport.objects.create(
            sighter=community_user,
            raw_engine_number="OTHER-OWNER-SYNC-001",
            sighting_date=date.today(),
            sighting_city="Karachi",
        )
        resp = owner_client.get(f"/api/sightings/{other_sighting.id}/")
        assert resp.status_code == 404

    def test_authority_can_retrieve_any_sighting_detail(
        self, authority_client, community_user
    ):
        from apps.sightings.models import SightingReport

        sighting = SightingReport.objects.create(
            sighter=community_user,
            raw_engine_number="AUTH-DETAIL-SYNC-001",
            sighting_date=date.today(),
            sighting_city="Lahore",
        )
        resp = authority_client.get(f"/api/sightings/{sighting.id}/")
        assert resp.status_code == 200

    def test_community_gets_404_on_another_users_sighting_detail(
        self, community_client, owner_user
    ):
        from apps.sightings.models import SightingReport

        other = SightingReport.objects.create(
            sighter=owner_user,
            raw_engine_number="COMM-OTHER-SYNC-001",
            sighting_date=date.today(),
            sighting_city="Karachi",
        )
        resp = community_client.get(f"/api/sightings/{other.id}/")
        assert resp.status_code == 404

    def test_unauthenticated_gets_401_on_sighting_list(self, api_client):
        resp = api_client.get("/api/sightings/")
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# 5. SIGHTING VERIFICATION FLOW
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestSightingVerificationFlow:
    """Authority verifies → owner is notified."""

    def test_authority_verifies_sighting_owner_gets_notification(
        self, authority_client, community_user, sample_bike, owner_user
    ):
        from apps.sightings.models import SightingReport
        from apps.notifications.notification_service import notify_sighting_verified
        from apps.notifications.models import Notification

        sighting = SightingReport.objects.create(
            sighter=community_user,
            raw_engine_number=sample_bike.engine_number,
            sighting_date=date.today(),
            sighting_city="Karachi",
            bike=sample_bike,
        )
        resp = authority_client.put(
            f"/api/sightings/{sighting.id}/verify/",
            {"bike_id": sample_bike.id}, format="json"
        )
        assert resp.status_code == 200
        assert resp.data["is_verified"] is True

        sighting.refresh_from_db()
        notify_sighting_verified(sighting)
        assert Notification.objects.filter(
            user=owner_user,
            type=Notification.Type.SIGHTING_MATCHED,
        ).exists()

    def test_owner_cannot_verify_sighting(
        self, owner_client, community_user, sample_bike
    ):
        from apps.sightings.models import SightingReport

        sighting = SightingReport.objects.create(
            sighter=community_user,
            raw_engine_number="OWNER-VERIFY-SYNC-001",
            sighting_date=date.today(),
            sighting_city="Karachi",
        )
        resp = owner_client.put(
            f"/api/sightings/{sighting.id}/verify/",
            {"bike_id": sample_bike.id}, format="json"
        )
        assert resp.status_code == 403

    def test_community_cannot_verify_sighting(
        self, community_client, community_user, sample_bike
    ):
        from apps.sightings.models import SightingReport

        sighting = SightingReport.objects.create(
            sighter=community_user,
            raw_engine_number="COMM-VERIFY-SYNC-001",
            sighting_date=date.today(),
            sighting_city="Karachi",
        )
        resp = community_client.put(
            f"/api/sightings/{sighting.id}/verify/",
            {"bike_id": sample_bike.id}, format="json"
        )
        assert resp.status_code == 403

    def test_verify_without_bike_id_returns_400_with_bike_id_in_error(
        self, authority_client, community_user
    ):
        from apps.sightings.models import SightingReport

        sighting = SightingReport.objects.create(
            sighter=community_user,
            raw_engine_number="VERIFY-NO-BIKE-SYNC-001",
            sighting_date=date.today(),
            sighting_city="Karachi",
        )
        resp = authority_client.put(
            f"/api/sightings/{sighting.id}/verify/", {}, format="json"
        )
        assert resp.status_code == 400
        assert "bike_id" in resp.data.get("error", "")


# ══════════════════════════════════════════════════════════════════════════════
# 6. NOTIFICATION DELIVERY PER ROLE
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestNotificationDeliveryPerRole:
    """Notification service functions route to the correct user per role."""

    def test_notify_theft_reported_creates_theft_reported_for_owner(
        self, sample_report, owner_user
    ):
        from apps.notifications.notification_service import notify_theft_reported
        from apps.notifications.models import Notification

        notify_theft_reported(sample_report)
        assert Notification.objects.filter(
            user=owner_user,
            type=Notification.Type.THEFT_REPORTED,
            report=sample_report,
        ).exists()

    def test_notify_status_changed_on_bike_located_notifies_owner(
        self, sample_report, owner_user
    ):
        from apps.notifications.notification_service import notify_status_changed
        from apps.notifications.models import Notification
        from apps.reports.models import TheftReport

        sample_report.status = TheftReport.Status.BIKE_LOCATED
        sample_report.save(update_fields=["status"])

        notify_status_changed(sample_report, TheftReport.Status.ACTIVE_INVESTIGATION)
        assert Notification.objects.filter(
            user=owner_user,
            type=Notification.Type.STATUS_UPDATE,
            report=sample_report,
        ).exists()

    def test_notify_status_changed_on_under_review_does_not_notify_owner(
        self, sample_report, owner_user
    ):
        from apps.notifications.notification_service import notify_status_changed
        from apps.notifications.models import Notification
        from apps.reports.models import TheftReport

        sample_report.status = TheftReport.Status.UNDER_REVIEW
        sample_report.save(update_fields=["status"])

        notify_status_changed(sample_report, TheftReport.Status.NEW_CASE)
        assert not Notification.objects.filter(
            user=owner_user,
            type=Notification.Type.STATUS_UPDATE,
            report=sample_report,
        ).exists()

    def test_high_confidence_sighting_alerts_authority_with_high_confidence_message(
        self, community_user, sample_bike, authority_user
    ):
        from apps.sightings.models import SightingReport
        from apps.notifications.notification_service import notify_sighting_submitted
        from apps.notifications.models import Notification

        authority_user.city = "Karachi"
        authority_user.save(update_fields=["city"])

        sighting = SightingReport.objects.create(
            sighter=community_user,
            top_match_bike=sample_bike,
            fuzzy_match_score=90,
            sighting_date=date.today(),
            sighting_city="Karachi",
        )
        notify_sighting_submitted(sighting)
        assert Notification.objects.filter(
            user=authority_user,
            type=Notification.Type.SYSTEM,
            message__icontains="high-confidence sighting",
        ).exists()

    def test_high_confidence_sighting_alerts_admin_with_review_pending_message(
        self, community_user, sample_bike, authority_user, admin_user
    ):
        from apps.sightings.models import SightingReport
        from apps.notifications.notification_service import notify_sighting_submitted
        from apps.notifications.models import Notification

        authority_user.city = "Karachi"
        authority_user.save(update_fields=["city"])

        sighting = SightingReport.objects.create(
            sighter=community_user,
            top_match_bike=sample_bike,
            fuzzy_match_score=90,
            sighting_date=date.today(),
            sighting_city="Karachi",
        )
        notify_sighting_submitted(sighting)
        assert Notification.objects.filter(
            user=admin_user,
            type=Notification.Type.SYSTEM,
            message__icontains="authority review pending",
        ).exists()

    def test_low_confidence_sighting_no_sighting_matched_for_owner(
        self, community_user, sample_bike
    ):
        from apps.sightings.models import SightingReport
        from apps.notifications.notification_service import notify_sighting_submitted
        from apps.notifications.models import Notification

        sighting = SightingReport.objects.create(
            sighter=community_user,
            top_match_bike=sample_bike,
            fuzzy_match_score=50,
            sighting_date=date.today(),
            sighting_city="Karachi",
        )
        notify_sighting_submitted(sighting)
        assert not Notification.objects.filter(
            user=sample_bike.owner,
            type=Notification.Type.SIGHTING_MATCHED,
        ).exists()

    def test_low_confidence_sighting_no_system_notification_for_authority(
        self, community_user, sample_bike, authority_user
    ):
        from apps.sightings.models import SightingReport
        from apps.notifications.notification_service import notify_sighting_submitted
        from apps.notifications.models import Notification

        authority_user.city = "Karachi"
        authority_user.save(update_fields=["city"])

        sighting = SightingReport.objects.create(
            sighter=community_user,
            top_match_bike=sample_bike,
            fuzzy_match_score=50,
            sighting_date=date.today(),
            sighting_city="Karachi",
        )
        Notification.objects.all().delete()
        notify_sighting_submitted(sighting)
        assert not Notification.objects.filter(
            user=authority_user,
            type=Notification.Type.SYSTEM,
        ).exists()

    def test_sighter_always_gets_system_receipt_notification(
        self, community_user
    ):
        from apps.sightings.models import SightingReport
        from apps.notifications.notification_service import notify_sighting_submitted
        from apps.notifications.models import Notification

        sighting = SightingReport.objects.create(
            sighter=community_user,
            sighting_date=date.today(),
            sighting_city="Karachi",
            raw_engine_number="RECEIPT-SYNC-001",
        )
        notify_sighting_submitted(sighting)
        assert Notification.objects.filter(user=community_user).exists()

    def test_owner_cannot_see_other_roles_notifications_in_api(
        self, owner_client, authority_user
    ):
        from apps.notifications.models import Notification

        Notification.objects.create(
            user=authority_user,
            type=Notification.Type.SYSTEM,
            message="Authority-only message",
            delivery_channel=Notification.Channel.IN_APP,
        )
        resp = owner_client.get("/api/notifications/")
        assert resp.status_code == 200
        assert resp.data["unread_count"] == 0


# ══════════════════════════════════════════════════════════════════════════════
# 7. RECOVERY FLOW — MULTI-ROLE
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestRecoveryFlowMultiRole:
    """Authority logs recovery → owner confirms → case closes."""

    def _advance_to_active_investigation(self, authority_client, report_id):
        """Helper: new_case → under_review → active_investigation."""
        authority_client.put(
            f"/api/reports/{report_id}/status/",
            {"status": "under_review"}, format="json"
        )
        authority_client.put(
            f"/api/reports/{report_id}/status/",
            {"status": "active_investigation"}, format="json"
        )

    def test_authority_logs_recovery_owner_can_get_recovery_date(
        self, owner_client, authority_client, sample_report
    ):
        self._advance_to_active_investigation(authority_client, sample_report.id)
        # Advance to bike_located (pre-condition for recovery endpoint)
        authority_client.put(
            f"/api/reports/{sample_report.id}/status/",
            {"status": "bike_located"}, format="json"
        )
        payload = {
            "recovery_date": str(date.today()),
            "recovery_city": "Karachi",
            "bike_condition": "good",
        }
        post_resp = authority_client.post(
            f"/api/reports/{sample_report.id}/recovery/", payload, format="json"
        )
        assert post_resp.status_code == 201

        get_resp = owner_client.get(f"/api/reports/{sample_report.id}/recovery/")
        assert get_resp.status_code == 200
        assert "recovery_date" in get_resp.data

    def test_owner_confirms_recovery_case_becomes_closed(
        self, owner_client, authority_client, sample_report
    ):
        self._advance_to_active_investigation(authority_client, sample_report.id)
        authority_client.put(
            f"/api/reports/{sample_report.id}/status/",
            {"status": "bike_located"}, format="json"
        )
        authority_client.post(
            f"/api/reports/{sample_report.id}/recovery/",
            {
                "recovery_date": str(date.today()),
                "recovery_city": "Karachi",
                "bike_condition": "good",
            },
            format="json"
        )
        sample_report.refresh_from_db()
        assert sample_report.status == "pending_verification"

        confirm_resp = owner_client.put(
            f"/api/reports/{sample_report.id}/recovery/confirm/", {}, format="json"
        )
        assert confirm_resp.status_code == 200
        sample_report.refresh_from_db()
        assert sample_report.status == "closed"
        assert sample_report.owner_recovery_confirmed is True

    def test_community_gets_404_on_recovery_get(
        self, community_client, sample_report
    ):
        resp = community_client.get(f"/api/reports/{sample_report.id}/recovery/")
        assert resp.status_code == 404

    def test_owner_cannot_confirm_recovery_for_another_owners_report(
        self, owner_client, owner_user_2, db
    ):
        from apps.bikes.models import Bike
        from apps.reports.models import TheftReport

        bike2 = Bike.objects.create(
            owner=owner_user_2,
            make="Suzuki", model="GS 150", year=2022,
            engine_number="SUZ22-RECOV-SYNC-001",
            chassis_number="SUZ22-RECOV-CHS-001",
        )
        report2 = TheftReport.objects.create(
            bike=bike2,
            reported_by=owner_user_2,
            theft_date=date.today(),
            theft_city="Karachi",
        )
        resp = owner_client.put(
            f"/api/reports/{report2.id}/recovery/confirm/", {}, format="json"
        )
        assert resp.status_code == 404

    def test_authority_cannot_call_recovery_confirm(
        self, authority_client, sample_report
    ):
        resp = authority_client.put(
            f"/api/reports/{sample_report.id}/recovery/confirm/", {}, format="json"
        )
        assert resp.status_code == 403

    def test_recovery_confirm_on_closed_report_returns_400(
        self, owner_client, admin_client, sample_report
    ):
        # Admin closes the case (authority no longer can do this directly)
        admin_client.put(
            f"/api/reports/{sample_report.id}/status/",
            {"status": "closed"}, format="json"
        )
        resp = owner_client.put(
            f"/api/reports/{sample_report.id}/recovery/confirm/", {}, format="json"
        )
        assert resp.status_code == 400


# ══════════════════════════════════════════════════════════════════════════════
# 8. OWNER HANDSHAKE — SIGHTING CONFIRMATION
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestOwnerHandshake:
    """Owner responds to sighting handshake; other roles are blocked."""

    def _pending_sighting(self, sample_bike, community_user, score=80):
        from apps.sightings.models import SightingReport
        return SightingReport.objects.create(
            sighter=community_user,
            top_match_bike=sample_bike,
            fuzzy_match_score=score,
            sighting_date=date.today(),
            sighting_city="Karachi",
            owner_confirmation_status="pending",
        )

    def test_owner_responds_yes_sets_confirmation_status(
        self, owner_client, sample_bike, community_user
    ):
        sighting = self._pending_sighting(sample_bike, community_user)
        resp = owner_client.put(
            f"/api/sightings/{sighting.id}/owner-confirm/",
            {"response": "yes"}, format="json"
        )
        assert resp.status_code == 200
        sighting.refresh_from_db()
        assert sighting.owner_confirmation_status == "yes"

    def test_owner_responds_no_archives_sighting(
        self, owner_client, sample_bike, community_user
    ):
        sighting = self._pending_sighting(sample_bike, community_user)
        resp = owner_client.put(
            f"/api/sightings/{sighting.id}/owner-confirm/",
            {"response": "no"}, format="json"
        )
        assert resp.status_code == 200
        sighting.refresh_from_db()
        assert sighting.is_archived is True

    def test_authority_cannot_confirm_sighting_on_behalf_of_owner(
        self, authority_client, sample_bike, community_user
    ):
        sighting = self._pending_sighting(sample_bike, community_user)
        resp = authority_client.put(
            f"/api/sightings/{sighting.id}/owner-confirm/",
            {"response": "yes"}, format="json"
        )
        assert resp.status_code == 403

    def test_community_cannot_call_owner_confirm(
        self, community_client, sample_bike, community_user
    ):
        sighting = self._pending_sighting(sample_bike, community_user)
        resp = community_client.put(
            f"/api/sightings/{sighting.id}/owner-confirm/",
            {"response": "yes"}, format="json"
        )
        assert resp.status_code == 403

    def test_invalid_response_value_returns_400(
        self, owner_client, sample_bike, community_user
    ):
        sighting = self._pending_sighting(sample_bike, community_user)
        resp = owner_client.put(
            f"/api/sightings/{sighting.id}/owner-confirm/",
            {"response": "maybe"}, format="json"
        )
        assert resp.status_code == 400

    def test_owner_cannot_confirm_sighting_for_another_owners_bike(
        self, owner_client, owner_user_2, community_user, db
    ):
        from apps.bikes.models import Bike
        from apps.sightings.models import SightingReport

        bike2 = Bike.objects.create(
            owner=owner_user_2,
            make="Suzuki", model="GS 150", year=2022,
            engine_number="SUZ22-HAND-SYNC-001",
            chassis_number="SUZ22-HAND-CHS-001",
        )
        sighting = SightingReport.objects.create(
            sighter=community_user,
            top_match_bike=bike2,
            fuzzy_match_score=80,
            sighting_date=date.today(),
            sighting_city="Karachi",
            owner_confirmation_status="pending",
        )
        # owner_client belongs to owner_user (not owner_user_2)
        resp = owner_client.put(
            f"/api/sightings/{sighting.id}/owner-confirm/",
            {"response": "yes"}, format="json"
        )
        assert resp.status_code == 404

    def test_double_confirmation_second_call_returns_400(
        self, owner_client, sample_bike, community_user
    ):
        sighting = self._pending_sighting(sample_bike, community_user)
        first = owner_client.put(
            f"/api/sightings/{sighting.id}/owner-confirm/",
            {"response": "yes"}, format="json"
        )
        assert first.status_code == 200

        second = owner_client.put(
            f"/api/sightings/{sighting.id}/owner-confirm/",
            {"response": "yes"}, format="json"
        )
        assert second.status_code == 400


# ══════════════════════════════════════════════════════════════════════════════
# 9. COMMUNITY CASE CLOSURE NOTIFICATION
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_case_closure_notifies_community_contributors(
    sample_report, community_user
):
    """Community members who submitted sightings are notified on case closure."""
    from apps.sightings.models import SightingReport
    from apps.notifications.notification_service import notify_case_closed_to_contributors
    from apps.notifications.models import Notification

    SightingReport.objects.create(
        sighter=community_user,
        top_match_bike=sample_report.bike,
        raw_engine_number=sample_report.bike.engine_number,
        sighting_date=date.today(),
        sighting_city="Karachi",
    )
    notify_case_closed_to_contributors(sample_report)
    assert Notification.objects.filter(
        user=community_user,
        type=Notification.Type.COMMUNITY_CLOSURE,
    ).exists()


# ══════════════════════════════════════════════════════════════════════════════
# 10. INVALID STATUS TRANSITIONS
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestInvalidStatusTransitions:
    """State machine rejects illegal jumps."""

    def test_authority_cannot_close_case_directly(
        self, authority_client, sample_report
    ):
        """Authority must never bypass the owner-confirmation flow by closing directly."""
        resp = authority_client.put(
            f"/api/reports/{sample_report.id}/status/",
            {"status": "closed"}, format="json"
        )
        assert resp.status_code == 403
        assert "owner" in resp.data.get("error", "").lower()

    def test_admin_can_close_case_directly(
        self, admin_client, sample_report
    ):
        """Admin retains the override right to close a case at any stage."""
        resp = admin_client.put(
            f"/api/reports/{sample_report.id}/status/",
            {"status": "closed"}, format="json"
        )
        assert resp.status_code == 200
        assert resp.data["new_status"] == "closed"

    def test_regression_under_review_to_new_case_returns_400(
        self, authority_client, sample_report
    ):
        authority_client.put(
            f"/api/reports/{sample_report.id}/status/",
            {"status": "under_review"}, format="json"
        )
        resp = authority_client.put(
            f"/api/reports/{sample_report.id}/status/",
            {"status": "new_case"}, format="json"
        )
        assert resp.status_code == 400
        assert "Cannot transition" in resp.data.get("error", "")

    def test_any_transition_on_closed_case_returns_400(
        self, authority_client, admin_client, sample_report
    ):
        # Admin closes the case first (authority cannot do this directly)
        admin_client.put(
            f"/api/reports/{sample_report.id}/status/",
            {"status": "closed"}, format="json"
        )
        # Now authority tries to re-open — must be rejected
        resp = authority_client.put(
            f"/api/reports/{sample_report.id}/status/",
            {"status": "under_review"}, format="json"
        )
        assert resp.status_code == 400

    def test_authority_cannot_advance_pending_verification_to_recovered(
        self, authority_client, sample_report
    ):
        """
        Once a case reaches pending_verification (after authority logs a
        recovery) the authority must NOT be able to advance it to recovered.
        Only the bike owner's /recovery/confirm/ endpoint can do that.
        """
        # Walk the report to pending_verification via legitimate transitions
        for s in ("under_review", "active_investigation", "bike_located"):
            authority_client.put(
                f"/api/reports/{sample_report.id}/status/",
                {"status": s}, format="json"
            )
        # Log recovery — moves the report to pending_verification
        authority_client.post(
            f"/api/reports/{sample_report.id}/recovery/",
            {
                "recovery_city":  "Karachi",
                "recovery_date":  "2024-01-15",
                "bike_condition": "good",
            },
            format="json",
        )
        # Authority tries to jump to recovered without owner confirmation
        resp = authority_client.put(
            f"/api/reports/{sample_report.id}/status/",
            {"status": "recovered"}, format="json"
        )
        assert resp.status_code == 403
        assert "owner" in resp.data.get("error", "").lower()

    def test_admin_can_advance_pending_verification_to_recovered(
        self, admin_client, authority_client, sample_report
    ):
        """Admin retains the right to move a case from pending_verification to recovered."""
        for s in ("under_review", "active_investigation", "bike_located"):
            authority_client.put(
                f"/api/reports/{sample_report.id}/status/",
                {"status": s}, format="json"
            )
        authority_client.post(
            f"/api/reports/{sample_report.id}/recovery/",
            {
                "recovery_city":  "Karachi",
                "recovery_date":  "2024-01-15",
                "bike_condition": "good",
            },
            format="json",
        )
        resp = admin_client.put(
            f"/api/reports/{sample_report.id}/status/",
            {"status": "recovered"}, format="json"
        )
        assert resp.status_code == 200
        assert resp.data["new_status"] == "recovered"


# ══════════════════════════════════════════════════════════════════════════════
# 11. END-TO-END DEMO NARRATIVE — "the presentation scenario"
# ══════════════════════════════════════════════════════════════════════════════
#
# A single test walks through the 6 canonical cross-role events in order.
# Each step is phrased as "THEN ..." to make failure output read like a script
# so a reviewer can see which beat of the demo broke.
#
#   Event 1 — Owner files report → Authority (same city) sees it in queue
#   Event 2 — Community submits sighting → ML fuzzy-matches to the stolen bike
#             → high-confidence alert reaches authority + admin
#   Event 3 — Authority verifies sighting → owner is notified + asked to confirm
#   Event 4 — Authority logs recovery → owner gets recovery-pending notification
#   Event 5 — Owner confirms pickup → status becomes RECOVERED → closed
#   Event 6 — Admin sees the full lifecycle reflected in audit logs
#
# All cross-city / permission / role-isolation aspects are already covered in the
# class-based tests above. This class is a HAPPY-PATH integration test whose
# primary value is catching regressions that slip between individually-passing
# unit tests.

@pytest.mark.django_db
class TestEndToEndDemoNarrative:
    """Single-test narrative covering every cross-role event in the demo script."""

    def test_full_demo_scenario_runs_end_to_end(
        self,
        owner_client, owner_user,
        authority_client, authority_user,
        community_client, community_user,
        admin_client, admin_user,
    ):
        """
        Runs the 6 presentation events in one pass.

        Notification types live on Notification.Type and are named:
            THEFT_REPORTED, STATUS_UPDATE, RECOVERY, SIGHTING_MATCHED,
            SIGHTING_OWNER_HANDSHAKE, SIGHTING_OWNER_RESPONSE, URGENT, SYSTEM.
        Permission-scoping and per-event edge cases are covered by the
        class-based tests above; this test asserts the happy path end-to-end.
        """
        from apps.bikes.models import Bike
        from apps.reports.models import TheftReport
        from apps.sightings.models import SightingReport
        from apps.notifications.models import Notification

        # ─── Setup: owner registers a bike ───────────────────────────────────
        bike = Bike.objects.create(
            owner=owner_user,
            make="Honda", model="CG 125", year=2023, color="Red",
            engine_number="HND23E9876543",
            chassis_number="MRHGC1250PY987654",
            registration_city="Karachi",
        )

        # ─── Event 1: Owner files theft report ───────────────────────────────
        # Outcomes: report created; owner gets THEFT_REPORTED receipt;
        #           report surfaces in the same-city authority's queue.
        file_resp = owner_client.post(
            "/api/reports/",
            {
                "bike": bike.id,
                "theft_date": str(date.today()),
                "theft_city": "Karachi",
                "description": "Parked outside market. Gone in 30 min.",
            },
            format="json",
        )
        assert file_resp.status_code == 201, f"Event 1 failed (owner file): {file_resp.data}"
        ref_number = file_resp.data["reference_number"]

        assert Notification.objects.filter(
            user=owner_user, type=Notification.Type.THEFT_REPORTED,
        ).exists(), "Event 1: owner did not receive THEFT_REPORTED receipt"

        queue_resp = authority_client.get("/api/reports/")
        assert queue_resp.status_code == 200
        refs_in_queue = [r["reference_number"] for r in queue_resp.data["results"]]
        assert ref_number in refs_in_queue, "Event 1: authority queue missing the new report"

        # reference_number is a @property (f"BTT-{id:04d}"), not a DB field —
        # derive the primary key from it.
        report = TheftReport.objects.get(pk=int(ref_number.split("-")[-1]))

        # Authority starts work on the case (realistic progression)
        authority_client.put(f"/api/reports/{report.id}/status/",
                             {"status": "under_review"}, format="json")
        authority_client.put(f"/api/reports/{report.id}/status/",
                             {"status": "active_investigation"}, format="json")

        # ─── Event 2: Community submits sighting — fuzzy match triggers ──────
        # Engine number has one-character typo so fuzzy match returns the bike.
        sighting_resp = community_client.post(
            "/api/sightings/",
            {
                "raw_engine_number": "HND23E9876534",  # transposed digits
                "sighting_date": str(date.today()),
                "sighting_city": "Karachi",
                "sighting_description": "Saw it chained near Tariq Road.",
            },
            format="json",
        )
        assert sighting_resp.status_code == 201, (
            f"Event 2 failed (community submit): {sighting_resp.data}"
        )
        # Sighting create serializer doesn't echo id — look it up by sighter.
        sighting = SightingReport.objects.filter(sighter=community_user).latest("created_at")
        assert sighting.top_match_bike_id == bike.id, (
            "Event 2: fuzzy match did not resolve to the stolen bike"
        )
        assert sighting.fuzzy_match_score and sighting.fuzzy_match_score >= 70, (
            f"Event 2: fuzzy score ({sighting.fuzzy_match_score}) below alert threshold"
        )
        # No photo + score ≥ 70 → owner handshake (see notify_sighting_submitted_extended).
        assert Notification.objects.filter(
            user=owner_user, type=Notification.Type.SIGHTING_OWNER_HANDSHAKE,
        ).exists(), "Event 2: owner did not receive SIGHTING_OWNER_HANDSHAKE prompt"

        # ─── Event 2b: Owner says 'yes' → authority urgently notified ────────
        handshake_resp = owner_client.put(
            f"/api/sightings/{sighting.id}/owner-confirm/",
            {"response": "yes"}, format="json",
        )
        assert handshake_resp.status_code == 200, (
            f"Event 2b failed (owner handshake yes): {handshake_resp.data}"
        )
        assert Notification.objects.filter(
            user=authority_user, type=Notification.Type.URGENT,
        ).exists(), "Event 2b: authority did not receive URGENT alert after owner confirmed"

        # ─── Event 3: Authority verifies sighting → owner notified ───────────
        verify_resp = authority_client.put(
            f"/api/sightings/{sighting.id}/verify/",
            {"bike_id": bike.id}, format="json",
        )
        assert verify_resp.status_code == 200, (
            f"Event 3 failed (authority verify): {verify_resp.data}"
        )
        sighting.refresh_from_db()
        assert sighting.is_verified is True
        assert Notification.objects.filter(
            user=owner_user, type=Notification.Type.SIGHTING_MATCHED,
        ).exists(), "Event 3: owner did not receive SIGHTING_MATCHED notification"

        # Move case to bike_located so recovery endpoint is valid
        authority_client.put(f"/api/reports/{report.id}/status/",
                             {"status": "bike_located"}, format="json")

        # ─── Event 4: Authority logs recovery → owner notified ───────────────
        recovery_resp = authority_client.post(
            f"/api/reports/{report.id}/recovery/",
            {
                "recovery_date": str(date.today()),
                "recovery_city": "Karachi",
                "bike_condition": "good",
                "notes": "Recovered with minor scratches.",
            },
            format="json",
        )
        assert recovery_resp.status_code in (200, 201), (
            f"Event 4 failed (authority log recovery): {recovery_resp.data}"
        )
        report.refresh_from_db()
        assert report.status == "pending_verification", (
            f"Event 4: expected pending_verification, got {report.status}"
        )
        assert Notification.objects.filter(
            user=owner_user, type=Notification.Type.RECOVERY,
        ).exists(), "Event 4: owner did not receive RECOVERY notification"

        # ─── Event 5: Owner confirms pickup → RECOVERED ──────────────────────
        confirm_resp = owner_client.put(
            f"/api/reports/{report.id}/recovery/confirm/",
            {"confirmed": True}, format="json",
        )
        assert confirm_resp.status_code == 200, (
            f"Event 5 failed (owner confirm pickup): {confirm_resp.data}"
        )
        report.refresh_from_db()
        assert report.status in ("recovered", "closed"), (
            f"Event 5: expected recovered/closed, got {report.status}"
        )
        assert report.owner_recovery_confirmed is True
        assert report.owner_recovery_confirmed_at is not None

        # ─── Event 6: Admin sees the full lifecycle in audit logs ────────────
        audit_resp = admin_client.get("/api/admin/audit-logs/")
        assert audit_resp.status_code == 200, (
            f"Event 6 failed (admin audit fetch): {audit_resp.status_code}"
        )
        entries = (
            audit_resp.data.get("results", audit_resp.data)
            if isinstance(audit_resp.data, dict) else audit_resp.data
        )
        actions_seen = {
            e["action"] for e in entries
            if isinstance(e, dict) and "action" in e
        }
        assert actions_seen, "Event 6: audit log empty — lifecycle not recorded"
