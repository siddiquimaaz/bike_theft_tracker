"""
tests/test_ml_corridors.py

Tests for:
  GET /api/ml/recovery-radius/  — recovery distance statistics
  GET /api/ml/corridors/        — theft-to-recovery corridor analysis

Covers:
  1. 202 when no fresh cache exists
  2. 200 with correct data when cache is fresh
  3. City-scoped queries return scoped data
  4. Authority can access both endpoints; owner/community cannot
  5. run_recovery_radius() computes correct mean/median/min/max
  6. run_corridor_analysis() returns corridors with expected fields
  7. Both functions skip gracefully with too few records
  8. trigger_reanalysis computes and caches corridor + radius results
"""
import pytest
from datetime import date, timedelta as dt
from django.utils import timezone


# ─── Cache fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def fresh_radius_cache(db):
    from apps.ml.models import MLAnalysisCache
    return MLAnalysisCache.objects.create(
        analysis_type=MLAnalysisCache.AnalysisType.RECOVERY_RADIUS,
        scope_city=None,
        computed_at=timezone.now(),
        expires_at=timezone.now() + dt(hours=12),
        result_data={
            "skipped": False,
            "mean_km": 12.5,
            "median_km": 10.2,
            "min_km": 1.0,
            "max_km": 30.0,
            "std_km": 5.3,
            "record_count": 8,
        },
        record_count=8,
    )


@pytest.fixture
def fresh_radius_cache_karachi(db):
    from apps.ml.models import MLAnalysisCache
    return MLAnalysisCache.objects.create(
        analysis_type=MLAnalysisCache.AnalysisType.RECOVERY_RADIUS,
        scope_city="Karachi",
        computed_at=timezone.now(),
        expires_at=timezone.now() + dt(hours=12),
        result_data={
            "skipped": False,
            "mean_km": 8.1,
            "median_km": 7.5,
            "min_km": 0.5,
            "max_km": 20.0,
            "std_km": 3.2,
            "record_count": 5,
        },
        record_count=5,
    )


@pytest.fixture
def fresh_corridor_cache(db):
    from apps.ml.models import MLAnalysisCache
    return MLAnalysisCache.objects.create(
        analysis_type=MLAnalysisCache.AnalysisType.CORRIDOR_ANALYSIS,
        scope_city=None,
        computed_at=timezone.now(),
        expires_at=timezone.now() + dt(hours=12),
        result_data={
            "skipped": False,
            "corridors": [
                {
                    "corridor_id": 0,
                    "bearing_deg": 45.0,
                    "bearing_label": "NE",
                    "mean_distance_km": 15.0,
                    "dx_mean_km": 10.6,
                    "dy_mean_km": 10.6,
                    "report_count": 7,
                },
                {
                    "corridor_id": 1,
                    "bearing_deg": 225.0,
                    "bearing_label": "SW",
                    "mean_distance_km": 8.0,
                    "dx_mean_km": -5.7,
                    "dy_mean_km": -5.7,
                    "report_count": 3,
                },
            ],
            "noise_points": 2,
            "record_count": 12,
            "overall_stats": {
                "dominant_bearing_deg": 45.0,
                "dominant_bearing_label": "NE",
                "mean_distance_km": 12.5,
                "record_count": 12,
            },
        },
        record_count=12,
    )


# ─── Recovery Radius endpoint tests ───────────────────────────────────────────

@pytest.mark.django_db
class TestRecoveryRadiusEndpoint:
    url = "/api/ml/recovery-radius/"

    def test_returns_202_when_no_cache(self, authority_client):
        resp = authority_client.get(self.url)
        assert resp.status_code == 202
        assert resp.data["data"] is None

    def test_returns_200_with_fresh_cache(self, authority_client, fresh_radius_cache):
        resp = authority_client.get(self.url)
        assert resp.status_code == 200
        assert resp.data["analysis_type"] == "recovery_radius"
        data = resp.data["data"]
        assert data["mean_km"] == 12.5
        assert data["median_km"] == 10.2
        assert data["record_count"] == 8

    def test_city_scoped_query(self, authority_client, fresh_radius_cache_karachi):
        resp = authority_client.get(self.url, {"city": "Karachi"})
        assert resp.status_code == 200
        assert resp.data["scope_city"] == "Karachi"
        assert resp.data["data"]["mean_km"] == 8.1

    def test_national_and_city_caches_are_independent(
        self, authority_client, fresh_radius_cache, fresh_radius_cache_karachi
    ):
        national = authority_client.get(self.url)
        karachi  = authority_client.get(self.url, {"city": "Karachi"})
        assert national.data["data"]["mean_km"] == 12.5
        assert karachi.data["data"]["mean_km"]  == 8.1

    def test_owner_cannot_access(self, owner_client, fresh_radius_cache):
        resp = owner_client.get(self.url)
        assert resp.status_code == 403

    def test_community_cannot_access(self, community_client, fresh_radius_cache):
        resp = community_client.get(self.url)
        assert resp.status_code == 403

    def test_unauthenticated_rejected(self, api_client, fresh_radius_cache):
        resp = api_client.get(self.url)
        assert resp.status_code == 401

    def test_admin_can_access(self, admin_client, fresh_radius_cache):
        resp = admin_client.get(self.url)
        assert resp.status_code == 200


# ─── Corridor Analysis endpoint tests ─────────────────────────────────────────

@pytest.mark.django_db
class TestCorridorAnalysisEndpoint:
    url = "/api/ml/corridors/"

    def test_returns_202_when_no_cache(self, authority_client):
        resp = authority_client.get(self.url)
        assert resp.status_code == 202

    def test_returns_200_with_fresh_cache(self, authority_client, fresh_corridor_cache):
        resp = authority_client.get(self.url)
        assert resp.status_code == 200
        assert resp.data["analysis_type"] == "corridor_analysis"
        data = resp.data["data"]
        assert len(data["corridors"]) == 2
        # Dominant corridor first
        assert data["corridors"][0]["bearing_label"] == "NE"
        assert data["corridors"][0]["report_count"]  == 7

    def test_corridors_have_required_fields(self, authority_client, fresh_corridor_cache):
        resp = authority_client.get(self.url)
        corridor = resp.data["data"]["corridors"][0]
        for field in ("corridor_id", "bearing_deg", "bearing_label", "mean_distance_km", "report_count"):
            assert field in corridor, f"Missing field: {field}"

    def test_overall_stats_present(self, authority_client, fresh_corridor_cache):
        resp = authority_client.get(self.url)
        stats = resp.data["data"]["overall_stats"]
        assert "dominant_bearing_label" in stats
        assert "mean_distance_km" in stats

    def test_owner_cannot_access(self, owner_client, fresh_corridor_cache):
        resp = owner_client.get(self.url)
        assert resp.status_code == 403

    def test_unauthenticated_rejected(self, api_client):
        resp = api_client.get(self.url)
        assert resp.status_code == 401

    def test_admin_can_access(self, admin_client, fresh_corridor_cache):
        resp = admin_client.get(self.url)
        assert resp.status_code == 200


# ─── run_recovery_radius() unit tests ─────────────────────────────────────────

_pair_counter = 0

def _make_theft_recovery_pair(owner, authority, theft_lat, theft_lng, rec_lat, rec_lng):
    """Helper: create a TheftReport with a RecoveryRecord having given coordinates."""
    global _pair_counter
    _pair_counter += 1

    from django.contrib.gis.geos import Point
    from apps.bikes.models import Bike
    from apps.reports.models import TheftReport, RecoveryRecord

    bike = Bike.objects.create(
        owner=owner,
        make="Honda", model="CB150", year=2020, color="Black",
        engine_number=f"ENGCOR{_pair_counter:05d}",
        chassis_number=f"CHSCOR{_pair_counter:05d}",
        registration_city="Karachi",
    )
    report = TheftReport.objects.create(
        bike=bike,
        reported_by=owner,
        theft_date=date.today(),
        theft_city="Karachi",
        theft_location=Point(theft_lng, theft_lat, srid=4326),
        status=TheftReport.Status.RECOVERED,
    )
    RecoveryRecord.objects.create(
        theft_report=report,
        logged_by=authority,
        recovery_date=date.today(),
        recovery_city="Karachi",
        recovery_location=Point(rec_lng, rec_lat, srid=4326),
        bike_condition="good",
    )
    return report


@pytest.mark.django_db
def test_recovery_radius_computes_correct_stats(owner_user, authority_user):
    """
    Three pairs with known coordinates — mean distance should be ~11.1 km.
    Karachi area:  theft=(24.86, 67.01), recovery pairs at ~5, ~10, ~20 km away.
    """
    from apps.ml.analysis import run_recovery_radius

    # ~5 km north
    _make_theft_recovery_pair(owner_user, authority_user, 24.86, 67.01, 24.905, 67.01)
    # ~10 km north
    _make_theft_recovery_pair(owner_user, authority_user, 24.86, 67.01, 24.950, 67.01)
    # ~18 km north
    _make_theft_recovery_pair(owner_user, authority_user, 24.86, 67.01, 25.022, 67.01)

    result = run_recovery_radius(city="Karachi")
    assert not result.get("skipped"), f"Should not skip with 3 records: {result}"
    assert result["record_count"] == 3
    assert result["mean_km"] > 0
    assert result["min_km"] < result["max_km"]
    assert result["median_km"] >= result["min_km"]
    assert result["median_km"] <= result["max_km"]


@pytest.mark.django_db
def test_recovery_radius_skips_with_too_few_records(db):
    """Zero paired records should return skipped=True."""
    from apps.ml.analysis import run_recovery_radius
    result = run_recovery_radius(city="Quetta")
    assert result.get("skipped") is True


# ─── run_corridor_analysis() unit tests ───────────────────────────────────────

@pytest.mark.django_db
def test_corridor_analysis_returns_corridors(owner_user, authority_user):
    """
    Create 4 NE-moving and 4 SW-moving pairs; expect 2 corridor clusters.
    """
    from apps.ml.analysis import run_corridor_analysis

    # 4 pairs moving NE (~10 km)
    for i in range(4):
        _make_theft_recovery_pair(
            owner_user, authority_user,
            24.86 + i * 0.001, 67.01 + i * 0.001,  # theft slightly varied
            24.95 + i * 0.001, 67.09 + i * 0.001,  # recovery ~NE
        )
    # 4 pairs moving SW (~8 km)
    for i in range(4):
        _make_theft_recovery_pair(
            owner_user, authority_user,
            24.86 + i * 0.001, 67.01 + i * 0.001,
            24.79 + i * 0.001, 66.94 + i * 0.001,  # recovery ~SW
        )

    result = run_corridor_analysis(city="Karachi")
    assert not result.get("skipped"), f"Should not skip: {result}"
    assert result["record_count"] == 8
    assert isinstance(result["corridors"], list)
    # At least one corridor identified
    assert len(result["corridors"]) >= 1
    # Each corridor has the required fields
    for corridor in result["corridors"]:
        assert "bearing_deg" in corridor
        assert "bearing_label" in corridor
        assert "mean_distance_km" in corridor
        assert "report_count" in corridor
    # Overall stats present
    assert "overall_stats" in result
    assert "dominant_bearing_label" in result["overall_stats"]


@pytest.mark.django_db
def test_corridor_analysis_skips_with_too_few_records(db):
    """Zero paired records should return skipped=True."""
    from apps.ml.analysis import run_corridor_analysis
    result = run_corridor_analysis(city="Quetta")
    assert result.get("skipped") is True
    assert result["corridors"] == []


@pytest.mark.django_db
def test_bearing_label_helper():
    """_bearing_label should return correct compass directions."""
    from apps.ml.analysis import _bearing_label
    assert _bearing_label(0)   == "N"
    assert _bearing_label(45)  == "NE"
    assert _bearing_label(90)  == "E"
    assert _bearing_label(180) == "S"
    assert _bearing_label(270) == "W"
    assert _bearing_label(315) == "NW"
    assert _bearing_label(360) == "N"  # full circle


# ─── Trigger reanalysis caches corridor + radius ───────────────────────────────

@pytest.mark.django_db
def test_trigger_reanalysis_caches_corridor_and_radius(admin_client, owner_user, authority_user):
    """
    POST /api/ml/trigger-reanalysis/ should compute and cache both
    corridor_analysis and recovery_radius (even if they skip due to no data).
    """
    from apps.ml.models import MLAnalysisCache

    # Create some paired data so the analyses don't all skip
    _make_theft_recovery_pair(owner_user, authority_user, 24.86, 67.01, 24.95, 67.09)
    _make_theft_recovery_pair(owner_user, authority_user, 24.87, 67.02, 24.94, 67.08)
    _make_theft_recovery_pair(owner_user, authority_user, 24.85, 67.00, 24.96, 67.10)

    resp = admin_client.post("/api/ml/trigger-reanalysis/")
    assert resp.status_code == 200

    # Both analysis types should now have cache entries
    assert MLAnalysisCache.objects.filter(
        analysis_type=MLAnalysisCache.AnalysisType.RECOVERY_RADIUS
    ).exists(), "recovery_radius cache should exist after reanalysis"

    assert MLAnalysisCache.objects.filter(
        analysis_type=MLAnalysisCache.AnalysisType.CORRIDOR_ANALYSIS
    ).exists(), "corridor_analysis cache should exist after reanalysis"
