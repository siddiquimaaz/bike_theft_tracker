from django.urls import path
from .views import (
    fuzzy_match,
    hotspot_clusters,
    trend_analytics,
    recovery_zones,
    recovery_radius,
    corridor_analysis,
    trigger_reanalysis,
)

urlpatterns = [
    path("fuzzy-match/",       fuzzy_match,       name="ml-fuzzy-match"),
    path("hotspots/",          hotspot_clusters,  name="ml-hotspots"),
    path("trends/",            trend_analytics,   name="ml-trends"),
    path("recovery-zones/",    recovery_zones,    name="ml-recovery-zones"),
    path("recovery-radius/",   recovery_radius,   name="ml-recovery-radius"),
    path("corridors/",         corridor_analysis, name="ml-corridors"),
    path("trigger-reanalysis/", trigger_reanalysis, name="ml-trigger-reanalysis"),
]
