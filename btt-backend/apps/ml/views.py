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


# ─── Manual Reanalysis Trigger ────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([IsAuthorityOrAdmin])
def trigger_reanalysis(request):
    """
    POST /api/ml/trigger-reanalysis/
    Admin triggers hotspot + trend recompute outside the cron schedule.
    Runs synchronously — may take a few seconds on large datasets.
    """
    import threading

    def _run():
        from .analysis import run_hotspot_analysis, save_hotspot_cache
        from .analysis import run_trend_analytics, save_trend_cache
        try:
            hotspot_result = run_hotspot_analysis()
            save_hotspot_cache(hotspot_result)
            logger.info("Manual reanalysis: hotspot complete")
        except Exception as exc:
            logger.error("Manual reanalysis: hotspot failed: %s", exc)
        try:
            trend_result = run_trend_analytics()
            save_trend_cache(trend_result)
            logger.info("Manual reanalysis: trends complete")
        except Exception as exc:
            logger.error("Manual reanalysis: trends failed: %s", exc)

    threading.Thread(target=_run, daemon=True).start()

    return Response({
        "message": "Reanalysis jobs started in background. Results will be available shortly."
    })
