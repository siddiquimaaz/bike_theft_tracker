"""
Bike Theft Tracker — Root URL Configuration
"""
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.users.urls.auth_urls")),
    path("api/bikes/", include("apps.bikes.urls")),
    path("api/reports/", include("apps.reports.urls")),
    path("api/sightings/", include("apps.sightings.urls")),
    path("api/notifications/", include("apps.notifications.urls")),
    path("api/ml/", include("apps.ml.urls")),
    path("api/admin/", include("apps.users.urls.admin_urls")),
    path("api/search/", include("apps.bikes.search_urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
