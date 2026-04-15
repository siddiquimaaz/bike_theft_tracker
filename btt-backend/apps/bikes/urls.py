from django.urls import path
from .views import BikeListCreateView, BikeDetailView

urlpatterns = [
    path("", BikeListCreateView.as_view(), name="bike-list-create"),
    path("<int:pk>/", BikeDetailView.as_view(), name="bike-detail"),
]
