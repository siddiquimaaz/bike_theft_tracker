"""
tests/test_admin.py
Admin endpoint tests — user management, analytics, authority creation, audit logs.
"""
import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestUserList:
    url = "/api/admin/users/"

    def test_admin_can_list_users(self, admin_client, owner_user, authority_user):
        response = admin_client.get(self.url)
        assert response.status_code == 200
        assert response.data["count"] >= 2

    def test_filter_by_role(self, admin_client, owner_user, authority_user):
        response = admin_client.get(self.url, {"role": "owner"})
        assert response.status_code == 200
        for user in response.data["results"]:
            assert user["role"] == "owner"

    def test_filter_by_is_active(self, admin_client, owner_user):
        response = admin_client.get(self.url, {"is_active": "true"})
        assert response.status_code == 200

    def test_filter_by_is_verified(self, admin_client, owner_user):
        response = admin_client.get(self.url, {"is_verified": "true"})
        assert response.status_code == 200

    def test_owner_cannot_list_users(self, owner_client):
        response = owner_client.get(self.url)
        assert response.status_code == 403

    def test_authority_cannot_list_users(self, authority_client):
        response = authority_client.get(self.url)
        assert response.status_code == 403

    def test_unauthenticated_rejected(self, api_client):
        response = api_client.get(self.url)
        assert response.status_code == 401


@pytest.mark.django_db
class TestCreateAuthority:
    url = "/api/admin/users/authority/"

    def test_admin_can_create_authority(self, admin_client):
        payload = {
            "full_name": "Officer Ali",
            "email": "officer.ali@test.btt",
            "cnic": "4200011112220",
            "badge_number": "KHI-009",
            "city": "Karachi",
            "password": "Test@12345",
        }
        response = admin_client.post(self.url, payload, format="json")
        assert response.status_code == 201

    def test_owner_cannot_create_authority(self, owner_client):
        payload = {
            "full_name": "Fake Officer",
            "email": "fake.officer@test.btt",
            "cnic": "4200011112221",
            "badge_number": "FAKE-001",
            "password": "Test@12345",
        }
        response = owner_client.post(self.url, payload, format="json")
        assert response.status_code == 403

    def test_unauthenticated_rejected(self, api_client):
        response = api_client.post(self.url, {})
        assert response.status_code == 401


@pytest.mark.django_db
class TestUserStatusUpdate:
    def test_admin_can_deactivate_user(self, admin_client, owner_user):
        url = f"/api/admin/users/{owner_user.id}/status/"
        response = admin_client.put(url, {"is_active": False}, format="json")
        assert response.status_code == 200
        assert "message" in response.data

    def test_admin_can_reactivate_user(self, admin_client, owner_user):
        url = f"/api/admin/users/{owner_user.id}/status/"
        response = admin_client.put(url, {"is_active": True}, format="json")
        assert response.status_code == 200

    def test_owner_cannot_update_status(self, owner_client, owner_user_2):
        url = f"/api/admin/users/{owner_user_2.id}/status/"
        response = owner_client.put(url, {"is_active": False}, format="json")
        assert response.status_code == 403

    def test_unauthenticated_rejected(self, api_client, owner_user):
        url = f"/api/admin/users/{owner_user.id}/status/"
        response = api_client.put(url, {"is_active": False})
        assert response.status_code == 401


@pytest.mark.django_db
class TestUserDelete:
    def test_admin_can_delete_authority_user(self, admin_client, authority_user):
        url = f"/api/admin/users/{authority_user.id}/"
        response = admin_client.delete(url)
        assert response.status_code == 204
        authority_user.refresh_from_db()
        assert authority_user.is_active is False
        assert authority_user.deleted_at is not None

    def test_owner_cannot_delete_users(self, owner_client, authority_user):
        url = f"/api/admin/users/{authority_user.id}/"
        response = owner_client.delete(url)
        assert response.status_code == 403

    def test_unauthenticated_delete_rejected(self, api_client, authority_user):
        url = f"/api/admin/users/{authority_user.id}/"
        response = api_client.delete(url)
        assert response.status_code == 401


@pytest.mark.django_db
class TestAnalyticsOverview:
    url = "/api/admin/analytics/"

    def test_admin_can_get_analytics(self, admin_client, sample_report):
        response = admin_client.get(self.url)
        assert response.status_code == 200
        assert "reports" in response.data
        assert "users" in response.data
        assert "city_breakdown" in response.data
        assert "unverified_sightings" in response.data
        assert "ml_cache_status" in response.data

    def test_admin_analytics_with_no_data(self, admin_client):
        response = admin_client.get(self.url)
        assert response.status_code == 200
        assert "reports" in response.data

    def test_authority_cannot_access_analytics(self, authority_client):
        response = authority_client.get(self.url)
        assert response.status_code == 403

    def test_owner_cannot_access_analytics(self, owner_client):
        response = owner_client.get(self.url)
        assert response.status_code == 403

    def test_unauthenticated_rejected(self, api_client):
        response = api_client.get(self.url)
        assert response.status_code == 401


@pytest.mark.django_db
class TestAuditLogs:
    url = "/api/admin/audit-logs/"

    def test_admin_can_list_audit_logs(self, admin_client):
        response = admin_client.get(self.url)
        assert response.status_code == 200

    def test_owner_cannot_access_audit_logs(self, owner_client):
        response = owner_client.get(self.url)
        assert response.status_code == 403

    def test_unauthenticated_rejected(self, api_client):
        response = api_client.get(self.url)
        assert response.status_code == 401
