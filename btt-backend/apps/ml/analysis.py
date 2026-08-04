"""
apps/ml/analysis.py
DBSCAN hotspot clustering, trend analytics, and recovery zone analysis.

All three are called from Django management commands (run via cron).
Results stored in MLAnalysisCache — dashboard reads from cache only.
"""
import logging
from datetime import timedelta

from apps.common.geo import EARTH_RADIUS_KM, haversine_km

logger = logging.getLogger(__name__)

# How long each cached analysis stays fresh.  Hotspot/corridor/radius are
# recomputed nightly, so 25h covers a run that starts a little late; trends run
# weekly and get 8 days for the same reason.
_DAILY_TTL = timedelta(hours=25)
_WEEKLY_TTL = timedelta(days=8)


def _save_cache(analysis_type, result: dict, city: str | None, ttl: timedelta):
    """Persist an analysis result to MLAnalysisCache with the given TTL."""
    from django.utils import timezone
    from .models import MLAnalysisCache
    MLAnalysisCache.objects.create(
        analysis_type=analysis_type,
        scope_city=city,
        result_data=result,
        expires_at=timezone.now() + ttl,
        record_count=result.get("record_count"),
    )


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
    eps_rad = settings.ML_DBSCAN_EPS / EARTH_RADIUS_KM  # convert km-ish degrees to radians
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

        # Approximate radius — max distance from centroid.  Vectorised over the
        # cluster rather than iterrows(), which materialises a Series per point.
        lats = np.radians(cluster_pts["lat"].to_numpy(dtype=float))
        lngs = np.radians(cluster_pts["lng"].to_numpy(dtype=float))
        c_lat, c_lng = np.radians(centroid_lat), np.radians(centroid_lng)
        a = (
            np.sin((lats - c_lat) / 2) ** 2
            + np.cos(c_lat) * np.cos(lats) * np.sin((lngs - c_lng) / 2) ** 2
        )
        max_radius_km = float(
            (2 * EARTH_RADIUS_KM * np.arctan2(np.sqrt(a), np.sqrt(1 - a))).max()
        )

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
    from .models import MLAnalysisCache
    _save_cache(MLAnalysisCache.AnalysisType.HOTSPOT_CLUSTERS, result, city, _DAILY_TTL)


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

    from django.conf import settings
    from apps.reports.models import TheftReport

    reports = list(
        TheftReport.objects.filter(deleted_at__isnull=True)
        .values("theft_city", "created_at", "status")
    )

    if not reports:
        return {"cities": [], "record_count": 0}

    df = pd.DataFrame(reports)
    # created_at is stored UTC-aware. Bucket by month in the project's own
    # timezone, not UTC: at UTC+5 a theft logged just after local midnight on
    # the 1st would otherwise land in the previous month on the dashboard.
    df["month"] = (
        pd.to_datetime(df["created_at"], utc=True)
        .dt.tz_convert(settings.TIME_ZONE)
        .dt.tz_localize(None)
        .dt.to_period("M")
        .astype(str)
    )
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
    from .models import MLAnalysisCache
    _save_cache(MLAnalysisCache.AnalysisType.TREND_ANALYTICS, result, None, _WEEKLY_TTL)


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


# ─── Recovery Radius Statistics ───────────────────────────────────────────────

def run_recovery_radius(city: str | None = None) -> dict:
    """
    For each theft report that has a matched RecoveryRecord, compute the
    straight-line haversine distance (km) between theft_location and
    recovery_location.  Returns mean, median, min, max, and std deviation.

    Args:
        city: Scope to a specific theft city, or None for national.

    Returns:
        dict with keys:
          mean_km, median_km, min_km, max_km, std_km,
          record_count, skipped
    """
    try:
        import numpy as np
    except ImportError as exc:
        logger.error("numpy missing: %s", exc)
        return {"error": str(exc)}

    from django.conf import settings
    from apps.reports.models import RecoveryRecord

    min_records = getattr(settings, "ML_MIN_RECORDS_FOR_CORRIDOR", 3)

    qs = RecoveryRecord.objects.filter(
        theft_report__theft_location__isnull=False,
        recovery_location__isnull=False,
        theft_report__deleted_at__isnull=True,
    ).select_related("theft_report")

    if city:
        qs = qs.filter(theft_report__theft_city__iexact=city)

    records = list(qs)

    if len(records) < min_records:
        logger.warning(
            "Recovery radius skipped — only %d paired records (minimum %d required)",
            len(records), min_records,
        )
        return {"skipped": True, "record_count": len(records)}

    distances = []
    for rec in records:
        t_loc = rec.theft_report.theft_location
        r_loc = rec.recovery_location
        if t_loc and r_loc:
            distances.append(haversine_km(t_loc.y, t_loc.x, r_loc.y, r_loc.x))

    if not distances:
        return {"skipped": True, "record_count": 0}

    arr = np.array(distances)
    result = {
        "skipped": False,
        "record_count": len(arr),
        "mean_km":   round(float(np.mean(arr)), 2),
        "median_km": round(float(np.median(arr)), 2),
        "min_km":    round(float(arr.min()), 2),
        "max_km":    round(float(arr.max()), 2),
        "std_km":    round(float(np.std(arr)), 2),
        "scope_city": city,
    }
    logger.info(
        "Recovery radius [%s]: %d records — mean=%.2f km, median=%.2f km",
        city or "national", len(arr), result["mean_km"], result["median_km"],
    )
    return result


def save_recovery_radius_cache(result: dict, city: str | None = None):
    """Persist recovery radius result with 25-hour TTL."""
    from .models import MLAnalysisCache
    _save_cache(MLAnalysisCache.AnalysisType.RECOVERY_RADIUS, result, city, _DAILY_TTL)


# ─── Theft-to-Recovery Corridor Analysis ──────────────────────────────────────

def _bearing_label(degrees: float) -> str:
    """Convert a compass bearing (0–360°) to a cardinal direction label."""
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    idx = int((degrees + 11.25) / 22.5) % 16
    return dirs[idx]


def run_corridor_analysis(city: str | None = None) -> dict:
    """
    DBSCAN on theft-to-recovery displacement vectors to identify common
    movement corridors — directions and distances bikes typically travel
    between theft point and recovery point.

    Each (theft_location, recovery_location) pair produces a 2D displacement
    vector (dx_km, dy_km).  DBSCAN clusters these to find dominant corridors.

    Args:
        city: Scope to a specific theft city, or None for national.

    Returns:
        dict with keys:
          corridors — list of cluster dicts:
            { corridor_id, bearing_deg, bearing_label, mean_distance_km,
              report_count, dx_mean_km, dy_mean_km }
          overall_stats — { dominant_bearing_label, dominant_bearing_deg,
                            mean_distance_km, record_count }
          noise_points, record_count, skipped
    """
    try:
        import numpy as np
        from sklearn.cluster import DBSCAN
    except ImportError as exc:
        logger.error("ML dependencies missing: %s", exc)
        return {"error": str(exc)}

    from math import atan2, cos, degrees, pi, radians
    from django.conf import settings
    from apps.reports.models import RecoveryRecord

    min_records = getattr(settings, "ML_MIN_RECORDS_FOR_CORRIDOR", 3)
    eps_km = 8.0    # corridors within 8 km of each other are grouped
    min_samples = getattr(settings, "ML_DBSCAN_MIN_SAMPLES", 3)

    qs = RecoveryRecord.objects.filter(
        theft_report__theft_location__isnull=False,
        recovery_location__isnull=False,
        theft_report__deleted_at__isnull=True,
    ).select_related("theft_report")

    if city:
        qs = qs.filter(theft_report__theft_city__iexact=city)

    records = list(qs)

    if len(records) < min_records:
        logger.warning(
            "Corridor analysis skipped — only %d paired records (minimum %d required)",
            len(records), min_records,
        )
        return {"skipped": True, "record_count": len(records), "corridors": [], "noise_points": 0}

    # Build displacement vector for each pair (in km, Cartesian approximation)
    km_per_degree = EARTH_RADIUS_KM * pi / 180
    vectors = []
    for rec in records:
        t_loc = rec.theft_report.theft_location
        r_loc = rec.recovery_location
        if not (t_loc and r_loc):
            continue
        t_lat, t_lng = t_loc.y, t_loc.x
        r_lat, r_lng = r_loc.y, r_loc.x
        # Convert degree deltas to km (flat-earth approximation, valid for <100 km)
        mid_lat = radians((t_lat + r_lat) / 2)
        dx_km = (r_lng - t_lng) * km_per_degree * cos(mid_lat)
        dy_km = (r_lat - t_lat) * km_per_degree
        vectors.append((dx_km, dy_km))

    if not vectors:
        return {"skipped": True, "record_count": 0, "corridors": [], "noise_points": 0}

    arr = np.array(vectors)  # shape (N, 2)

    # DBSCAN on displacement vectors — eps in km-space
    db = DBSCAN(eps=eps_km, min_samples=min_samples, algorithm="ball_tree").fit(arr)

    corridors = []
    for cluster_id in sorted(set(db.labels_)):
        if cluster_id == -1:
            continue
        mask = db.labels_ == cluster_id
        cluster_vecs = arr[mask]

        dx_mean = float(cluster_vecs[:, 0].mean())
        dy_mean = float(cluster_vecs[:, 1].mean())

        # Bearing: angle from North, clockwise (0° = N, 90° = E, 180° = S, 270° = W)
        bearing = (degrees(atan2(dx_mean, dy_mean)) + 360) % 360
        dist_km = float(np.sqrt(dx_mean**2 + dy_mean**2))

        corridors.append({
            "corridor_id":      int(cluster_id),
            "bearing_deg":      round(bearing, 1),
            "bearing_label":    _bearing_label(bearing),
            "mean_distance_km": round(dist_km, 2),
            "dx_mean_km":       round(dx_mean, 2),
            "dy_mean_km":       round(dy_mean, 2),
            "report_count":     int(mask.sum()),
        })

    # Sort by report count descending — dominant corridor first
    corridors.sort(key=lambda c: c["report_count"], reverse=True)

    noise_count = int((db.labels_ == -1).sum())

    # Overall stats across all pairs (not just clustered ones)
    all_bearings = [
        (degrees(atan2(v[0], v[1])) + 360) % 360
        for v in vectors
    ]
    all_distances = [float(np.sqrt(v[0]**2 + v[1]**2)) for v in vectors]
    mean_bearing = float(np.mean(all_bearings)) if all_bearings else 0.0
    mean_distance = round(float(np.mean(all_distances)), 2) if all_distances else 0.0

    logger.info(
        "Corridor analysis [%s]: %d corridors, %d noise points from %d records",
        city or "national", len(corridors), noise_count, len(vectors),
    )
    return {
        "skipped": False,
        "corridors": corridors,
        "noise_points": noise_count,
        "record_count": len(vectors),
        "overall_stats": {
            "dominant_bearing_deg":   round(mean_bearing, 1),
            "dominant_bearing_label": _bearing_label(mean_bearing),
            "mean_distance_km":       mean_distance,
            "record_count":           len(vectors),
        },
    }


def save_corridor_cache(result: dict, city: str | None = None):
    """Persist corridor analysis result with 25-hour TTL."""
    from .models import MLAnalysisCache
    _save_cache(MLAnalysisCache.AnalysisType.CORRIDOR_ANALYSIS, result, city, _DAILY_TTL)
