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
    city = request.query_params.get("city", None)

    from .models import MLAnalysisCache
    cache = MLAnalysisCache.get_fresh(MLAnalysisCache.AnalysisType.HOTSPOT_CLUSTERS, city=city)

    if not cache:
        return Response(
            {
                "message": (
                    "Hotspot analysis cache is stale or not yet computed. "
                    "Results will be available after the next scheduled cron job (daily 2 AM). "
                    "Admin can trigger recompute at POST /api/ml/trigger-reanalysis/."
                ),
                "data": None,
            },
            status=status.HTTP_202_ACCEPTED,
        )

    return Response({
        "analysis_type": "hotspot_clusters",
        "scope_city": city,
        "computed_at": cache.computed_at,
        "expires_at": cache.expires_at,
        "record_count": cache.record_count,
        "data": cache.result_data,
    })


# ─── Trend Analytics ──────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAdminUser])
def trend_analytics(request):
    """
    GET /api/ml/trends/
    Returns cached monthly theft/recovery counts and recovery rates per city.
    """
    from .models import MLAnalysisCache
    cache = MLAnalysisCache.get_fresh(MLAnalysisCache.AnalysisType.TREND_ANALYTICS)

    if not cache:
        return Response(
            {
                "message": (
                    "Trend analytics cache is stale or not yet computed. "
                    "Runs every Sunday at 3 AM. "
                    "Admin can trigger recompute at POST /api/ml/trigger-reanalysis/."
                ),
                "data": None,
            },
            status=status.HTTP_202_ACCEPTED,
        )

    return Response({
        "analysis_type": "trend_analytics",
        "computed_at": cache.computed_at,
        "expires_at": cache.expires_at,
        "record_count": cache.record_count,
        "data": cache.result_data,
    })


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
    city = request.query_params.get("city", None)

    from .models import MLAnalysisCache
    cache = MLAnalysisCache.get_fresh(MLAnalysisCache.AnalysisType.RECOVERY_RADIUS, city=city)

    if not cache:
        return Response(
            {
                "message": (
                    "Recovery radius cache is stale or not yet computed. "
                    "Results will be available after the next scheduled run. "
                    "Admin can trigger recompute at POST /api/ml/trigger-reanalysis/."
                ),
                "data": None,
            },
            status=status.HTTP_202_ACCEPTED,
        )

    return Response({
        "analysis_type": "recovery_radius",
        "scope_city": city,
        "computed_at": cache.computed_at,
        "expires_at": cache.expires_at,
        "record_count": cache.record_count,
        "data": cache.result_data,
    })


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
    city = request.query_params.get("city", None)

    from .models import MLAnalysisCache
    cache = MLAnalysisCache.get_fresh(MLAnalysisCache.AnalysisType.CORRIDOR_ANALYSIS, city=city)

    if not cache:
        return Response(
            {
                "message": (
                    "Corridor analysis cache is stale or not yet computed. "
                    "Admin can trigger recompute at POST /api/ml/trigger-reanalysis/."
                ),
                "data": None,
            },
            status=status.HTTP_202_ACCEPTED,
        )

    return Response({
        "analysis_type": "corridor_analysis",
        "scope_city": city,
        "computed_at": cache.computed_at,
        "expires_at": cache.expires_at,
        "record_count": cache.record_count,
        "data": cache.result_data,
    })


# ─── Manual Reanalysis Trigger ────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([IsAdminUser])
def trigger_reanalysis(request):
    """
    POST /api/ml/trigger-reanalysis/
    Admin triggers hotspot + trend + corridor + radius recompute outside the cron schedule.
    Runs synchronously so the frontend can refetch immediately after the 200 returns.
    """
    from .analysis import (
        run_hotspot_analysis, save_hotspot_cache,
        run_trend_analytics, save_trend_cache,
        run_corridor_analysis, save_corridor_cache,
        run_recovery_radius, save_recovery_radius_cache,
    )

    job_results = {}

    try:
        hotspot_result = run_hotspot_analysis()
        save_hotspot_cache(hotspot_result)
        job_results["hotspot"] = "ok"
        logger.info("Manual reanalysis: hotspot complete")
    except Exception as exc:
        logger.error("Manual reanalysis: hotspot failed: %s", exc)
        job_results["hotspot"] = f"error: {exc}"

    try:
        trend_result = run_trend_analytics()
        save_trend_cache(trend_result)
        job_results["trends"] = "ok"
        logger.info("Manual reanalysis: trends complete")
    except Exception as exc:
        logger.error("Manual reanalysis: trends failed: %s", exc)
        job_results["trends"] = f"error: {exc}"

    try:
        corridor_result = run_corridor_analysis()
        save_corridor_cache(corridor_result)
        job_results["corridors"] = "ok"
        logger.info("Manual reanalysis: corridors complete")
    except Exception as exc:
        logger.error("Manual reanalysis: corridors failed: %s", exc)
        job_results["corridors"] = f"error: {exc}"

    try:
        radius_result = run_recovery_radius()
        save_recovery_radius_cache(radius_result)
        job_results["radius"] = "ok"
        logger.info("Manual reanalysis: recovery radius complete")
    except Exception as exc:
        logger.error("Manual reanalysis: recovery radius failed: %s", exc)
        job_results["radius"] = f"error: {exc}"

    return Response({
        "message": "Reanalysis complete. Dashboard data is ready.",
        "results": job_results,
    })
