"""
tests/test_ml.py
ML endpoint tests — fuzzy match, hotspot clusters, trend analytics,
recovery zones, and trigger reanalysis.
"""
import pytest
from datetime import date
from django.utils import timezone
from datetime import timedelta


@pytest.fixture
def fresh_hotspot_cache(db):
    from apps.ml.models import MLAnalysisCache
    return MLAnalysisCache.objects.create(
        analysis_type=MLAnalysisCache.AnalysisType.HOTSPOT_CLUSTERS,
        scope_city=None,
        computed_at=timezone.now(),
        expires_at=timezone.now() + timedelta(hours=12),
        result_data={"clusters": [{"lat": 24.86, "lng": 67.01, "count": 5}]},
        record_count=10,
    )


@pytest.fixture
def fresh_trend_cache(db):
    from apps.ml.models import MLAnalysisCache
    return MLAnalysisCache.objects.create(
        analysis_type=MLAnalysisCache.AnalysisType.TREND_ANALYTICS,
        scope_city=None,
        computed_at=timezone.now(),
        expires_at=timezone.now() + timedelta(hours=24),
        result_data={"monthly": [{"month": "2026-01", "thefts": 12, "recoveries": 3}]},
        record_count=20,
    )


@pytest.fixture
def city_hotspot_cache(db):
    from apps.ml.models import MLAnalysisCache
    return MLAnalysisCache.objects.create(
        analysis_type=MLAnalysisCache.AnalysisType.HOTSPOT_CLUSTERS,
        scope_city="Karachi",
        computed_at=timezone.now(),
        expires_at=timezone.now() + timedelta(hours=12),
        result_data={"clusters": [{"lat": 24.86, "lng": 67.01, "count": 3}]},
        record_count=5,
    )


@pytest.mark.django_db
class TestFuzzyMatch:
    url = "/api/ml/fuzzy-match/"

    def test_authority_can_fuzzy_match_engine(self, authority_client, sample_report):
        response = authority_client.get(self.url, {"engine": "HND22A1234567"})
        assert response.status_code == 200
        assert "results" in response.data
        assert response.data["field"] == "engine_number"

    def test_authority_can_fuzzy_match_chassis(self, authority_client, sample_report):
        response = authority_client.get(self.url, {"chassis": "MRHGC1250NY123456"})
        assert response.status_code == 200
        assert response.data["field"] == "chassis_number"

    def test_missing_params_returns_400(self, authority_client):
        response = authority_client.get(self.url)
        assert response.status_code == 400
        assert "error" in response.data

    def test_short_query_returns_400(self, authority_client):
        response = authority_client.get(self.url, {"engine": "AB"})
        assert response.status_code == 400

    def test_owner_cannot_access_fuzzy_match(self, owner_client):
        response = owner_client.get(self.url, {"engine": "HND22A1234567"})
        assert response.status_code == 403

    def test_community_cannot_access_fuzzy_match(self, community_client):
        response = community_client.get(self.url, {"engine": "HND22A1234567"})
        assert response.status_code == 403

    def test_unauthenticated_rejected(self, api_client):
        response = api_client.get(self.url, {"engine": "HND22A1234567"})
        assert response.status_code == 401

    def test_no_stolen_bikes_returns_empty(self, authority_client):
        response = authority_client.get(self.url, {"engine": "HND22A1234567"})
        assert response.status_code == 200
        assert response.data["results"] == []


@pytest.mark.django_db
class TestHotspotClusters:
    url = "/api/ml/hotspots/"

    def test_authority_gets_stale_cache_202(self, authority_client):
        response = authority_client.get(self.url)
        assert response.status_code == 202
        assert response.data["data"] is None

    def test_authority_gets_fresh_cache_200(self, authority_client, fresh_hotspot_cache):
        response = authority_client.get(self.url)
        assert response.status_code == 200
        assert response.data["analysis_type"] == "hotspot_clusters"
        assert "data" in response.data

    def test_city_filter(self, authority_client, city_hotspot_cache):
        response = authority_client.get(self.url, {"city": "Karachi"})
        assert response.status_code == 200
        assert response.data["scope_city"] == "Karachi"

    def test_admin_can_access(self, admin_client, fresh_hotspot_cache):
        response = admin_client.get(self.url)
        assert response.status_code == 200

    def test_owner_cannot_access(self, owner_client):
        response = owner_client.get(self.url)
        assert response.status_code == 403

    def test_unauthenticated_rejected(self, api_client):
        response = api_client.get(self.url)
        assert response.status_code == 401


@pytest.mark.django_db
class TestTrendAnalytics:
    url = "/api/ml/trends/"

    def test_admin_gets_stale_cache_202(self, admin_client):
        response = admin_client.get(self.url)
        assert response.status_code == 202
        assert response.data["data"] is None

    def test_admin_gets_fresh_cache_200(self, admin_client, fresh_trend_cache):
        response = admin_client.get(self.url)
        assert response.status_code == 200
        assert response.data["analysis_type"] == "trend_analytics"

    def test_authority_cannot_access_trends(self, authority_client):
        response = authority_client.get(self.url)
        assert response.status_code == 403

    def test_owner_cannot_access_trends(self, owner_client):
        response = owner_client.get(self.url)
        assert response.status_code == 403

    def test_unauthenticated_rejected(self, api_client):
        response = api_client.get(self.url)
        assert response.status_code == 401


@pytest.mark.django_db
class TestRecoveryZones:
    url = "/api/ml/recovery-zones/"

    def test_admin_can_query_recovery_zones(self, admin_client):
        response = admin_client.get(self.url, {"lat": "24.86", "lng": "67.01"})
        assert response.status_code == 200

    def test_missing_lat_lng_returns_400(self, admin_client):
        response = admin_client.get(self.url)
        assert response.status_code == 400
        assert "error" in response.data

    def test_invalid_lat_returns_400(self, admin_client):
        response = admin_client.get(self.url, {"lat": "999", "lng": "67.01"})
        assert response.status_code == 400

    def test_invalid_lng_returns_400(self, admin_client):
        response = admin_client.get(self.url, {"lat": "24.86", "lng": "999"})
        assert response.status_code == 400

    def test_invalid_radius_returns_400(self, admin_client):
        response = admin_client.get(self.url, {"lat": "24.86", "lng": "67.01", "radius_km": "500"})
        assert response.status_code == 400

    def test_authority_cannot_access(self, authority_client):
        response = authority_client.get(self.url, {"lat": "24.86", "lng": "67.01"})
        assert response.status_code == 403

    def test_owner_cannot_access(self, owner_client):
        response = owner_client.get(self.url, {"lat": "24.86", "lng": "67.01"})
        assert response.status_code == 403

    def test_unauthenticated_rejected(self, api_client):
        response = api_client.get(self.url, {"lat": "24.86", "lng": "67.01"})
        assert response.status_code == 401

    def test_custom_radius(self, admin_client):
        response = admin_client.get(self.url, {"lat": "24.86", "lng": "67.01", "radius_km": "10"})
        assert response.status_code == 200

    def test_non_numeric_lat_returns_400(self, admin_client):
        response = admin_client.get(self.url, {"lat": "abc", "lng": "67.01"})
        assert response.status_code == 400


@pytest.mark.django_db
class TestTriggerReanalysis:
    url = "/api/ml/trigger-reanalysis/"

    def test_admin_can_trigger_reanalysis(self, admin_client):
        response = admin_client.post(self.url)
        assert response.status_code == 200
        assert "message" in response.data

    def test_authority_cannot_trigger(self, authority_client):
        response = authority_client.post(self.url)
        assert response.status_code == 403

    def test_owner_cannot_trigger(self, owner_client):
        response = owner_client.post(self.url)
        assert response.status_code == 403

    def test_unauthenticated_rejected(self, api_client):
        response = api_client.post(self.url)
        assert response.status_code == 401
