from django.urls import path
from .views import public_bike_search, city_report_count

urlpatterns = [
    path("bike/", public_bike_search, name="search-bike"),
    path("city/<str:city>/", city_report_count, name="search-city"),
]
