from django.urls import path
from .views import SightingListCreateView, SightingDetailView, verify_sighting, owner_confirm_sighting

urlpatterns = [
    path("", SightingListCreateView.as_view(), name="sighting-list-create"),
    path("<int:pk>/", SightingDetailView.as_view(), name="sighting-detail"),
    path("<int:pk>/verify/", verify_sighting, name="sighting-verify"),
    path("<int:pk>/owner-confirm/", owner_confirm_sighting, name="sighting-owner-confirm"),
]
