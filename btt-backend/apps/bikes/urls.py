from django.urls import path
from .views import BikeListCreateView, BikeDetailView, StolenBikeListView

urlpatterns = [
    path("", BikeListCreateView.as_view(), name="bike-list-create"),
    path("stolen/", StolenBikeListView.as_view(), name="bike-stolen-list"),
    path("<int:pk>/", BikeDetailView.as_view(), name="bike-detail"),
]
