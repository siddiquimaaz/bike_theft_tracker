"""
tests/test_security.py
Security and RBAC tests:
  - Unauthenticated requests return 401
  - Owner token on authority endpoints → 403
  - Authority token on admin endpoints → 403
  - SQL injection attempts rejected
  - OWASP-inspired role escalation checks
"""
import pytest


@pytest.mark.django_db
class TestAuthenticationRequired:
    """All protected endpoints must return 401 without a token."""

    endpoints_401 = [
        ("GET",  "/api/bikes/"),
        ("POST", "/api/bikes/"),
        ("GET",  "/api/reports/"),
        ("POST", "/api/reports/"),
        ("GET",  "/api/notifications/"),
        ("GET",  "/api/ml/hotspots/"),
        ("GET",  "/api/admin/users/"),
        ("GET",  "/api/admin/analytics/"),
    ]

    @pytest.mark.parametrize("method,url", endpoints_401)
    def test_unauthenticated_returns_401(self, api_client, method, url):
        response = getattr(api_client, method.lower())(url)
        assert response.status_code == 401, (
            f"{method} {url} returned {response.status_code} — expected 401"
        )


@pytest.mark.django_db
class TestRoleEscalation:
    """Owner credentials must be refused on authority/admin endpoints."""

    def test_owner_cannot_access_ml_fuzzy_match(self, owner_client):
        response = owner_client.get("/api/ml/fuzzy-match/?engine=TEST")
        assert response.status_code == 403

    def test_owner_cannot_access_ml_hotspots(self, owner_client):
        response = owner_client.get("/api/ml/hotspots/")
        assert response.status_code == 403

    def test_owner_cannot_access_admin_users(self, owner_client):
        response = owner_client.get("/api/admin/users/")
        assert response.status_code == 403

    def test_owner_cannot_create_authority(self, owner_client):
        response = owner_client.post("/api/admin/users/authority/", {})
        assert response.status_code == 403

    def test_owner_cannot_view_audit_logs(self, owner_client):
        response = owner_client.get("/api/admin/audit-logs/")
        assert response.status_code == 403

    def test_authority_cannot_access_admin_analytics(self, authority_client):
        response = authority_client.get("/api/admin/analytics/")
        assert response.status_code == 403

    def test_authority_cannot_trigger_reanalysis(self, authority_client):
        response = authority_client.post("/api/ml/trigger-reanalysis/")
        assert response.status_code == 403

    def test_authority_cannot_delete_report(self, authority_client, sample_report):
        url = f"/api/reports/{sample_report.id}/"
        response = authority_client.delete(url)
        assert response.status_code == 403

    def test_community_cannot_file_report(self, community_client, sample_bike):
        from datetime import date
        payload = {
            "bike": sample_bike.id,
            "theft_date": str(date.today()),
            "theft_city": "Karachi",
        }
        response = community_client.post("/api/reports/", payload)
        assert response.status_code == 403


@pytest.mark.django_db
class TestObjectLevelSecurity:
    """Users cannot access or modify resources they don't own."""

    def test_owner_cannot_see_other_owners_report(
        self, owner_client, owner_user_2, sample_bike, db
    ):
        from apps.bikes.models import Bike
        from apps.reports.models import TheftReport
        from datetime import date

        other_bike = Bike.objects.create(
            owner=owner_user_2, make="Yamaha", model="YBR 125", year=2021,
            engine_number="OTHERSEC00001", chassis_number="OTHERSECCHASSIS001",
        )
        other_report = TheftReport.objects.create(
            bike=other_bike, reported_by=owner_user_2,
            theft_date=date.today(), theft_city="Lahore", status="stolen",
        )
        # owner_client should NOT see this report
        response = owner_client.get(f"/api/reports/{other_report.id}/")
        assert response.status_code == 404

    def test_owner_cannot_delete_own_bike_with_active_report(
        self, owner_client, sample_bike, sample_report
    ):
        response = owner_client.delete(f"/api/bikes/{sample_bike.id}/")
        assert response.status_code == 400


@pytest.mark.django_db
class TestSQLInjection:
    """Input that looks like SQL should be safely handled by ORM parameterization."""

    def test_sql_injection_in_search_query(self, api_client):
        malicious = "' OR '1'='1"
        response = api_client.get(f"/api/search/bike/?q={malicious}")
        # Should return 200 with empty results — not a DB error
        assert response.status_code in (200, 400)
        if response.status_code == 200:
            assert response.data["count"] == 0

    def test_sql_injection_in_city(self, api_client):
        malicious = "Karachi'; DROP TABLE theft_reports; --"
        response = api_client.get(f"/api/search/city/{malicious}/")
        # Must not crash — ORM protects against this
        assert response.status_code == 200
        assert "active_theft_reports" in response.data


@pytest.mark.django_db
class TestUnverifiedUserRestrictions:
    """Unverified email users cannot file reports or register bikes."""

    @pytest.fixture
    def unverified_client(self, db):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create_user(
            email="unverified@sec.btt",
            full_name="Unverified",
            password="Test@12345",
            role="owner",
            is_verified=False,
        )
        from rest_framework_simplejwt.tokens import RefreshToken
        from rest_framework.test import APIClient
        client = APIClient()
        refresh = RefreshToken.for_user(user)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
        return client

    def test_unverified_owner_cannot_register_bike(self, unverified_client):
        payload = {
            "make": "Honda", "model": "CD 70", "year": 2020,
            "engine_number": "UNVER00000001", "chassis_number": "UNVERCHASSIS0001",
        }
        response = unverified_client.post("/api/bikes/", payload)
        assert response.status_code == 403
