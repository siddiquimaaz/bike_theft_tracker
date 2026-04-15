"""
apps/ml/analysis.py
DBSCAN hotspot clustering, trend analytics, and recovery zone analysis.

All three are called from Django management commands (run via cron).
Results stored in MLAnalysisCache — dashboard reads from cache only.
"""
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)


# ─── DBSCAN Hotspot Clustering ────────────────────────────────────────────────

def run_hotspot_analysis(city: str | None = None) -> dict:
    """
    Run DBSCAN on the last 6 months of theft reports to identify hotspot zones.

    Parameters
    ----------
    city : str | None
        Scope to a specific city or None for national analysis.

    Returns
    -------
    dict with keys:
        clusters     — list of cluster dicts (centroid lat/lng, report count)
        noise_points — count of unclustered reports
        record_count — total theft records analysed
        skipped      — True if insufficient data
    """
    try:
        import numpy as np
        import pandas as pd
        from sklearn.cluster import DBSCAN
    except ImportError as exc:
        logger.error("ML dependencies missing: %s", exc)
        return {"error": str(exc)}

    from django.conf import settings
    from django.utils import timezone
    from apps.reports.models import TheftReport

    cutoff = timezone.now() - timedelta(days=settings.ML_HOTSPOT_LOOKBACK_DAYS)

    qs = TheftReport.objects.filter(
        theft_location__isnull=False,
        created_at__gte=cutoff,
        deleted_at__isnull=True,
    )
    if city:
        qs = qs.filter(theft_city__iexact=city)

    # Extract lat/lng via PostGIS annotation
    records = list(qs.values("theft_location__x", "theft_location__y", "id"))

    if len(records) < settings.ML_MIN_RECORDS_FOR_CLUSTERING:
        logger.warning(
            "Hotspot analysis skipped — only %d records (minimum %d required)",
            len(records), settings.ML_MIN_RECORDS_FOR_CLUSTERING,
        )
        return {"skipped": True, "record_count": len(records), "clusters": [], "noise_points": 0}

    df = pd.DataFrame(records)
    df.rename(columns={
        "theft_location__x": "lng",
        "theft_location__y": "lat",
    }, inplace=True)
    df.dropna(subset=["lat", "lng"], inplace=True)

    coords = df[["lat", "lng"]].values

    # DBSCAN with haversine metric — eps in radians, min_samples from settings
    eps_rad = settings.ML_DBSCAN_EPS / 6371.0  # convert km-ish degrees to radians
    db = DBSCAN(
        eps=eps_rad,
        min_samples=settings.ML_DBSCAN_MIN_SAMPLES,
        algorithm="ball_tree",
        metric="haversine",
    ).fit(np.radians(coords))

    df["cluster"] = db.labels_

    clusters = []
    for cluster_id in sorted(set(db.labels_)):
        if cluster_id == -1:
            continue  # noise points
        cluster_pts = df[df["cluster"] == cluster_id]
        centroid_lat = float(cluster_pts["lat"].mean())
        centroid_lng = float(cluster_pts["lng"].mean())

        # Approximate radius — max distance from centroid
        from math import radians, sin, cos, sqrt, atan2
        def haversine_km(lat1, lng1, lat2, lng2):
            R = 6371
            dlat = radians(lat2 - lat1)
            dlng = radians(lng2 - lng1)
            a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
            return 2 * R * atan2(sqrt(a), sqrt(1 - a))

        max_radius_km = 0.0
        for _, row in cluster_pts.iterrows():
            d = haversine_km(centroid_lat, centroid_lng, row["lat"], row["lng"])
            if d > max_radius_km:
                max_radius_km = d

        clusters.append({
            "cluster_id": int(cluster_id),
            "centroid_lat": centroid_lat,
            "centroid_lng": centroid_lng,
            "report_count": int(len(cluster_pts)),
            "radius_km": round(max_radius_km, 3),
        })

    # Sort clusters by report count — largest first
    clusters.sort(key=lambda c: c["report_count"], reverse=True)

    noise_count = int((db.labels_ == -1).sum())
    logger.info(
        "Hotspot analysis complete: %d clusters, %d noise points from %d records",
        len(clusters), noise_count, len(df),
    )
    return {
        "skipped": False,
        "clusters": clusters,
        "noise_points": noise_count,
        "record_count": len(df),
    }


def save_hotspot_cache(result: dict, city: str | None = None):
    """Persist DBSCAN result to MLAnalysisCache with 25-hour TTL."""
    from django.utils import timezone
    from .models import MLAnalysisCache
    MLAnalysisCache.objects.create(
        analysis_type=MLAnalysisCache.AnalysisType.HOTSPOT_CLUSTERS,
        scope_city=city,
        result_data=result,
        expires_at=timezone.now() + timedelta(hours=25),
        record_count=result.get("record_count"),
    )


# ─── Trend Analytics ──────────────────────────────────────────────────────────

def run_trend_analytics() -> dict:
    """
    Compute monthly theft/recovery counts and recovery rates per city.
    Uses pandas groupby on the full theft_reports table.

    Returns
    -------
    dict with key 'cities' — list of:
      { city, month (YYYY-MM), theft_count, recovery_count, recovery_rate_pct }
    """
    try:
        import pandas as pd
    except ImportError as exc:
        logger.error("pandas missing: %s", exc)
        return {"error": str(exc)}

    from apps.reports.models import TheftReport

    reports = list(
        TheftReport.objects.filter(deleted_at__isnull=True)
        .values("theft_city", "created_at", "status")
    )

    if not reports:
        return {"cities": [], "record_count": 0}

    df = pd.DataFrame(reports)
    df["month"] = pd.to_datetime(df["created_at"]).dt.to_period("M").astype(str)
    df["is_recovered"] = df["status"] == "recovered"

    grouped = (
        df.groupby(["theft_city", "month"])
        .agg(
            theft_count=("status", "count"),
            recovery_count=("is_recovered", "sum"),
        )
        .reset_index()
    )
    grouped["recovery_rate_pct"] = (
        grouped["recovery_count"] / grouped["theft_count"] * 100
    ).round(2)

    # National aggregation
    national = (
        df.groupby("month")
        .agg(theft_count=("status", "count"), recovery_count=("is_recovered", "sum"))
        .reset_index()
    )
    national["recovery_rate_pct"] = (
        national["recovery_count"] / national["theft_count"] * 100
    ).round(2)
    national["theft_city"] = "__national__"

    combined = pd.concat([grouped, national], ignore_index=True)
    combined = combined.sort_values(["theft_city", "month"])

    logger.info("Trend analytics complete: %d records processed", len(df))
    return {
        "cities": combined.rename(columns={"theft_city": "city"}).to_dict(orient="records"),
        "record_count": len(df),
    }


def save_trend_cache(result: dict):
    """Persist trend analytics result with 8-day TTL."""
    from django.utils import timezone
    from .models import MLAnalysisCache
    MLAnalysisCache.objects.create(
        analysis_type=MLAnalysisCache.AnalysisType.TREND_ANALYTICS,
        scope_city=None,
        result_data=result,
        expires_at=timezone.now() + timedelta(days=8),
        record_count=result.get("record_count"),
    )


# ─── Recovery Zone Analysis ────────────────────────────────────────────────────

def get_recovery_zones(lat: float, lng: float, radius_km: float = 20) -> dict:
    """
    PostGIS ST_DWithin query: given a theft location, return historical
    recovery coordinates of bikes stolen from nearby.

    This is an on-demand query — not cached — because the input point varies.

    Args:
        lat, lng    : Centre point of the query area
        radius_km   : Search radius in kilometres

    Returns:
        dict with 'recovery_points' list of {lat, lng, recovery_date, city}
    """
    from django.contrib.gis.geos import Point
    from django.contrib.gis.measure import Distance
    from apps.reports.models import TheftReport, RecoveryRecord

    center = Point(lng, lat, srid=4326)
    radius_m = radius_km * 1000

    nearby_reports = TheftReport.objects.filter(
        theft_location__distance_lte=(center, Distance(m=radius_m)),
        status__in=["recovered", "closed"],
        deleted_at__isnull=True,
    ).values_list("id", flat=True)

    recoveries = RecoveryRecord.objects.filter(
        theft_report_id__in=nearby_reports,
        recovery_location__isnull=False,
    ).only("recovery_location", "recovery_date", "recovery_city")

    points = [
        {
            "lat": r.recovery_location.y,
            "lng": r.recovery_location.x,
            "recovery_date": str(r.recovery_date),
            "city": r.recovery_city,
        }
        for r in recoveries
    ]

    logger.info(
        "Recovery zone analysis: centre=(%.4f, %.4f) radius=%.1fkm → %d points",
        lat, lng, radius_km, len(points),
    )
    return {
        "query": {"lat": lat, "lng": lng, "radius_km": radius_km},
        "recovery_points": points,
        "count": len(points),
    }
