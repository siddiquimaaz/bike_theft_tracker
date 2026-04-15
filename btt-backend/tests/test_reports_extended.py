"""
tests/test_reports_extended.py
Additional report tests: delete, recovery GET/PUT, permissions, edge cases.
"""
import pytest
from datetime import date


@pytest.mark.django_db
class TestReportDelete:
    def test_admin_can_soft_delete_report(self, admin_client, sample_report):
        url = f"/api/reports/{sample_report.id}/"
        response = admin_client.delete(url)
        assert response.status_code == 204
        sample_report.refresh_from_db()
        assert sample_report.deleted_at is not None

    def test_owner_cannot_delete_report(self, owner_client, sample_report):
        url = f"/api/reports/{sample_report.id}/"
        response = owner_client.delete(url)
        assert response.status_code == 403

    def test_authority_cannot_delete_report(self, authority_client, sample_report):
        url = f"/api/reports/{sample_report.id}/"
        response = authority_client.delete(url)
        assert response.status_code == 403

    def test_unauthenticated_cannot_delete(self, api_client, sample_report):
        url = f"/api/reports/{sample_report.id}/"
        response = api_client.delete(url)
        assert response.status_code == 401


@pytest.mark.django_db
class TestRecoveryRecordExtended:
    def test_authority_gets_full_recovery_detail(self, authority_client, recovered_report):
        url = f"/api/reports/{recovered_report.id}/recovery/"
        response = authority_client.get(url)
        assert response.status_code == 200
        # Authority should see full serializer output including logged_by_id
        assert "logged_by_id" in response.data

    def test_get_recovery_when_none_exists(self, owner_client, sample_report):
        url = f"/api/reports/{sample_report.id}/recovery/"
        response = owner_client.get(url)
        assert response.status_code == 404
        assert "No recovery record" in response.data["error"]

    def test_owner_cannot_log_recovery(self, owner_client, sample_report):
        sample_report.status = "under_investigation"
        sample_report.save(update_fields=["status"])
        url = f"/api/reports/{sample_report.id}/recovery/"
        payload = {
            "recovery_date": str(date.today()),
            "recovery_city": "Karachi",
            "bike_condition": "good",
        }
        response = owner_client.post(url, payload)
        assert response.status_code == 403

    def test_recovery_record_not_found_for_other_user(self, owner_client, owner_user_2, db):
        from apps.bikes.models import Bike
        from apps.reports.models import TheftReport
        other_bike = Bike.objects.create(
            owner=owner_user_2, make="Yamaha", model="YBR 125", year=2021,
            engine_number="YAM21B9999999", chassis_number="YAM21CHASSIS00001",
        )
        report = TheftReport.objects.create(
            bike=other_bike,
            reported_by=owner_user_2,
            theft_date=date.today(),
            theft_city="Lahore",
            status="stolen",
        )
        url = f"/api/reports/{report.id}/recovery/"
        response = owner_client.get(url)
        assert response.status_code == 404

    def test_authority_can_amend_recovery(self, authority_client, recovered_report):
        url = f"/api/reports/{recovered_report.id}/recovery/"
        payload = {"bike_condition": "damaged", "recovery_city": "Karachi"}
        response = authority_client.put(url, payload)
        assert response.status_code == 200
        assert response.data["bike_condition"] == "damaged"

    def test_owner_cannot_amend_recovery(self, owner_client, recovered_report):
        url = f"/api/reports/{recovered_report.id}/recovery/"
        response = owner_client.put(url, {"bike_condition": "damaged"})
        assert response.status_code == 403

    def test_amend_nonexistent_recovery_returns_404(self, authority_client, sample_report):
        url = f"/api/reports/{sample_report.id}/recovery/"
        response = authority_client.put(url, {"bike_condition": "good"})
        assert response.status_code == 404


@pytest.mark.django_db
class TestPermissionClasses:
    """Direct unit tests for permission classes not exercised via views."""

    def test_is_community_allows_community_user(self, community_user):
        from rest_framework.test import APIRequestFactory
        from apps.users.permissions import IsCommunity
        factory = APIRequestFactory()
        request = factory.get("/")
        request.user = community_user
        perm = IsCommunity()
        assert perm.has_permission(request, None) is True

    def test_is_community_rejects_owner(self, owner_user):
        from rest_framework.test import APIRequestFactory
        from apps.users.permissions import IsCommunity
        factory = APIRequestFactory()
        request = factory.get("/")
        request.user = owner_user
        perm = IsCommunity()
        assert perm.has_permission(request, None) is False

    def test_is_owner_or_authority_allows_owner(self, owner_user):
        from rest_framework.test import APIRequestFactory
        from apps.users.permissions import IsOwnerOrAuthority
        factory = APIRequestFactory()
        request = factory.get("/")
        request.user = owner_user
        perm = IsOwnerOrAuthority()
        assert perm.has_permission(request, None) is True

    def test_is_owner_or_authority_allows_authority(self, authority_user):
        from rest_framework.test import APIRequestFactory
        from apps.users.permissions import IsOwnerOrAuthority
        factory = APIRequestFactory()
        request = factory.get("/")
        request.user = authority_user
        perm = IsOwnerOrAuthority()
        assert perm.has_permission(request, None) is True

    def test_is_owner_or_authority_rejects_community(self, community_user):
        from rest_framework.test import APIRequestFactory
        from apps.users.permissions import IsOwnerOrAuthority
        factory = APIRequestFactory()
        request = factory.get("/")
        request.user = community_user
        perm = IsOwnerOrAuthority()
        assert perm.has_permission(request, None) is False

    def test_is_resource_owner_allows_owner_on_write(self, owner_user, sample_bike):
        from rest_framework.test import APIRequestFactory
        from apps.users.permissions import IsResourceOwner
        factory = APIRequestFactory()
        request = factory.put("/")
        request.user = owner_user
        perm = IsResourceOwner()
        # sample_bike.owner == owner_user
        assert perm.has_object_permission(request, None, sample_bike) is True

    def test_is_resource_owner_rejects_non_owner(self, owner_user_2, sample_bike):
        from rest_framework.test import APIRequestFactory
        from apps.users.permissions import IsResourceOwner
        factory = APIRequestFactory()
        request = factory.put("/")
        request.user = owner_user_2
        perm = IsResourceOwner()
        assert perm.has_object_permission(request, None, sample_bike) is False

    def test_is_resource_owner_allows_read_for_anyone(self, owner_user_2, sample_bike):
        from rest_framework.test import APIRequestFactory
        from apps.users.permissions import IsResourceOwner
        factory = APIRequestFactory()
        request = factory.get("/")
        request.user = owner_user_2
        perm = IsResourceOwner()
        assert perm.has_object_permission(request, None, sample_bike) is True


@pytest.mark.django_db
class TestBikeSerializerValidation:
    def test_invalid_year_rejected(self, owner_client):
        payload = {
            "make": "Honda",
            "model": "CB 150",
            "year": 1800,
            "color": "Red",
            "engine_number": "ENG1800001",
            "chassis_number": "CHS1800001",
        }
        response = owner_client.post("/api/bikes/", payload)
        assert response.status_code == 400
