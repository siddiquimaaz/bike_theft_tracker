"""
apps/ml/models.py
Pre-computed ML result cache — avoids running heavy analysis on every request.
Dashboard reads from cache; cron jobs write to it.
"""
from django.db import models
from django.utils import timezone


class MLAnalysisCache(models.Model):
    class AnalysisType(models.TextChoices):
        HOTSPOT_CLUSTERS  = "hotspot_clusters",  "Hotspot Clusters (DBSCAN)"
        TREND_ANALYTICS   = "trend_analytics",   "Trend Analytics (pandas)"
        RECOVERY_ZONES    = "recovery_zones",    "Recovery Zone Analysis (PostGIS)"
        CORRIDOR_ANALYSIS = "corridor_analysis", "Theft-to-Recovery Corridor Analysis (DBSCAN)"
        RECOVERY_RADIUS   = "recovery_radius",   "Recovery Radius Statistics"

    analysis_type = models.CharField(max_length=30, choices=AnalysisType.choices)
    scope_city = models.CharField(
        max_length=80, null=True, blank=True,
        help_text="NULL = national analysis; city name = city-scoped analysis"
    )
    computed_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(
        help_text="Dashboard uses cache if NOW() < expires_at; otherwise triggers recompute"
    )
    result_data = models.JSONField(
        help_text="Full ML output: cluster centroids, trend series, zone coordinates"
    )
    record_count = models.IntegerField(
        null=True, blank=True,
        help_text="Records used in this analysis — shown for data freshness context"
    )

    class Meta:
        db_table = "ml_analysis_cache"
        ordering = ["-computed_at"]

    def __str__(self):
        scope = self.scope_city or "national"
        return f"{self.analysis_type} [{scope}] computed {self.computed_at:%Y-%m-%d %H:%M}"

    @property
    def is_fresh(self):
        return timezone.now() < self.expires_at

    @classmethod
    def get_fresh(cls, analysis_type, city=None):
        """Return the most recent non-expired cache entry, or None."""
        return cls.objects.filter(
            analysis_type=analysis_type,
            scope_city=city,
            expires_at__gt=timezone.now(),
        ).order_by("-computed_at").first()
