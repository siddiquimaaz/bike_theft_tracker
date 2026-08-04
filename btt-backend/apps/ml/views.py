"""
apps/ml/views.py
ML API endpoints — all read from cache or run on-demand.
No heavy computation happens synchronously in a request cycle
(except fuzzy match which is fast, and recovery zones which use PostGIS index).
"""
import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status

from apps.users.permissions import IsAuthority, IsAuthorityOrAdmin, IsAdminUser

logger = logging.getLogger(__name__)


def _cached_analysis_response(analysis_type, stale_message, city=None, scoped=True):
    """
    Serve a cached ML analysis.

    Every analysis endpoint answers the same two ways: 200 with the cached
    payload, or 202 with a "not computed yet" notice telling the caller how to
    force a recompute.  `scoped` controls whether the response echoes the city
    back — the national-only analyses have no scope to report.
    """
    from .models import MLAnalysisCache
    cache = MLAnalysisCache.get_fresh(analysis_type, city=city)

    if not cache:
        return Response(
            {"message": stale_message, "data": None},
            status=status.HTTP_202_ACCEPTED,
        )

    payload = {
        "analysis_type": analysis_type,
        "computed_at": cache.computed_at,
        "expires_at": cache.expires_at,
        "record_count": cache.record_count,
        "data": cache.result_data,
    }
    if scoped:
        payload["scope_city"] = city
    return Response(payload)


# ─── Fuzzy Match ──────────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthority])
def fuzzy_match(request):
    """
    GET /api/ml/fuzzy-match/?engine={number}
    GET /api/ml/fuzzy-match/?chassis={number}

    Runs rapidfuzz WRatio against all stolen engine/chassis numbers.
    Returns top 5 matches with confidence labels and bike/owner info.
    Authority must manually confirm the match before submitting recovery.
    """
    engine_q = request.query_params.get("engine", "").strip()
    chassis_q = request.query_params.get("chassis", "").strip()

    if not engine_q and not chassis_q:
        return Response(
            {"error": "Provide 'engine' or 'chassis' query parameter."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    query = engine_q or chassis_q
    field = "engine_number" if engine_q else "chassis_number"

    if len(query) < 3:
        return Response(
            {"error": "Query must be at least 3 characters."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    from .fuzzy_match import find_fuzzy_matches
    results = find_fuzzy_matches(query, field=field, limit=5)

    return Response({
        "query": query,
        "field": field,
        "results": results,
        "count": len(results),
    })


# ─── Hotspot Clusters ─────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthorityOrAdmin])
def hotspot_clusters(request):
    """
    GET /api/ml/hotspots/?city={city}
    Returns cached DBSCAN cluster data: centroid lat/lng, report count, radius.
    If cache is stale or absent, returns a 202 with a recompute notice.
    """
    from .models import MLAnalysisCache
    return _cached_analysis_response(
        MLAnalysisCache.AnalysisType.HOTSPOT_CLUSTERS,
        "Hotspot analysis cache is stale or not yet computed. "
        "Results will be available after the next scheduled cron job (daily 2 AM). "
        "Admin can trigger recompute at POST /api/ml/trigger-reanalysis/.",
        city=request.query_params.get("city", None),
    )


# ─── Trend Analytics ──────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAdminUser])
def trend_analytics(request):
    """
    GET /api/ml/trends/
    Returns cached monthly theft/recovery counts and recovery rates per city.
    """
    from .models import MLAnalysisCache
    return _cached_analysis_response(
        MLAnalysisCache.AnalysisType.TREND_ANALYTICS,
        "Trend analytics cache is stale or not yet computed. "
        "Runs every Sunday at 3 AM. "
        "Admin can trigger recompute at POST /api/ml/trigger-reanalysis/.",
        scoped=False,  # national only — no city to echo back
    )


# ─── Recovery Zone Analysis ───────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAdminUser])
def recovery_zones(request):
    """
    GET /api/ml/recovery-zones/?lat={lat}&lng={lng}&radius_km={radius}
    PostGIS ST_DWithin: historical recovery locations near a given theft point.
    On-demand — not cached — because the centre point varies per request.
    """
    try:
        lat = float(request.query_params["lat"])
        lng = float(request.query_params["lng"])
        radius_km = float(request.query_params.get("radius_km", 20))
    except (KeyError, ValueError):
        return Response(
            {"error": "lat and lng are required numeric query parameters."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
        return Response(
            {"error": "lat must be -90–90, lng must be -180–180."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not (0 < radius_km <= 200):
        return Response(
            {"error": "radius_km must be between 1 and 200."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    from .analysis import get_recovery_zones
    result = get_recovery_zones(lat, lng, radius_km)
    return Response(result)


# ─── Recovery Radius ──────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthorityOrAdmin])
def recovery_radius(request):
    """
    GET /api/ml/recovery-radius/?city={city}

    Returns cached statistics about how far (in km) stolen bikes typically
    travel between the theft location and the recovery location.
    Authority can scope to their own city; Admin can query any city or national.

    Response (200):
      { mean_km, median_km, min_km, max_km, std_km, record_count, scope_city }
    Response (202): cache stale — recompute pending.
    """
    from .models import MLAnalysisCache
    return _cached_analysis_response(
        MLAnalysisCache.AnalysisType.RECOVERY_RADIUS,
        "Recovery radius cache is stale or not yet computed. "
        "Results will be available after the next scheduled run. "
        "Admin can trigger recompute at POST /api/ml/trigger-reanalysis/.",
        city=request.query_params.get("city", None),
    )


# ─── Corridor Analysis ────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthorityOrAdmin])
def corridor_analysis(request):
    """
    GET /api/ml/corridors/?city={city}

    Returns cached DBSCAN clusters of theft-to-recovery displacement vectors,
    showing which directions and distances stolen bikes commonly travel.

    Each corridor cluster contains:
      bearing_deg, bearing_label (e.g. "NE"), mean_distance_km, report_count

    Response (200): fresh cache data.
    Response (202): cache stale.
    """
    from .models import MLAnalysisCache
    return _cached_analysis_response(
        MLAnalysisCache.AnalysisType.CORRIDOR_ANALYSIS,
        "Corridor analysis cache is stale or not yet computed. "
        "Admin can trigger recompute at POST /api/ml/trigger-reanalysis/.",
        city=request.query_params.get("city", None),
    )


# ─── Manual Reanalysis Trigger ────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([IsAdminUser])
def trigger_reanalysis(request):
    """
    POST /api/ml/trigger-reanalysis/
    Admin triggers hotspot + trend + corridor + radius recompute outside the cron schedule.
    Runs synchronously so the frontend can refetch immediately after the 200 returns.
    """
    # Imported as a module, not by name, so that tests patching
    # apps.ml.analysis.* are seen by the lookups below.
    from . import analysis

    jobs = (
        ("hotspot",   "run_hotspot_analysis",  "save_hotspot_cache"),
        ("trends",    "run_trend_analytics",   "save_trend_cache"),
        ("corridors", "run_corridor_analysis", "save_corridor_cache"),
        ("radius",    "run_recovery_radius",   "save_recovery_radius_cache"),
    )

    job_results = {}
    for name, run_attr, save_attr in jobs:
        try:
            result = getattr(analysis, run_attr)()
            getattr(analysis, save_attr)(result)
            job_results[name] = "ok"
            logger.info("Manual reanalysis: %s complete", name)
        except Exception as exc:
            logger.error("Manual reanalysis: %s failed: %s", name, exc)
            job_results[name] = f"error: {exc}"

    return Response({
        "message": "Reanalysis complete. Dashboard data is ready.",
        "results": job_results,
    })
