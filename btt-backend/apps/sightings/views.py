"""
apps/sightings/views.py
Community sighting submission — auto-runs fuzzy match on POST.
Authority verifies sightings, which notifies the bike owner.
"""
import logging
from django.db.models import Q
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.bikes.models import Bike
from apps.common.api import error_response, get_object_or_none
from apps.common.background import deferred_task, run_in_background
from apps.common.city import cities_match
from apps.users.permissions import IsAnyAuthenticatedRole, IsAuthorityOrAdmin, IsOwner
from .models import SightingReport
from .serializers import SightingCreateSerializer, SightingListSerializer

logger = logging.getLogger(__name__)

NOT_FOUND_ERROR = "Sighting not found."
NO_CITY_ERROR = "Your account has no city configured. Contact an admin."


class SightingListCreateView(generics.ListCreateAPIView):
    """
    POST /api/sightings/  — Any authenticated user submits sighting
    GET  /api/sightings/  — Role-scoped:
         Authority/Admin → all unverified sightings (sorted by confidence)
         Owner/Community  → only their own sightings (all statuses)
    """
    permission_classes = [IsAnyAuthenticatedRole]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return SightingCreateSerializer
        return SightingListSerializer

    def get_queryset(self):
        user = self.request.user
        qs = SightingReport.objects.select_related("top_match_bike", "top_match_bike__owner")
        if user.is_authority or user.is_admin:
            # Authority/Admin: unverified sightings sorted by match confidence
            return qs.filter(is_verified=False).order_by("-fuzzy_match_score", "-created_at")
        if user.is_owner:
            # Owner sees:
            #   1. Sightings they personally submitted (community role behaviour)
            #   2. Unarchived, pending sightings where the top-matched bike is theirs
            #      (the ones they need to confirm/deny)
            return (
                qs.filter(
                    Q(sighter=user) |
                    Q(
                        top_match_bike__owner=user,
                        owner_confirmation_status="pending",
                        is_archived=False,
                    )
                )
                .distinct()
                .order_by("-created_at")
            )
        # Community: their own submissions only
        return qs.filter(sighter=user).order_by("-created_at")

    def perform_create(self, serializer):
        sighting = serializer.save(sighter=self.request.user)
        run_in_background(_notify_sighting_submitted, sighting)


class SightingDetailView(generics.RetrieveAPIView):
    """GET /api/sightings/{id}/ — Full sighting detail with fuzzy match candidate"""
    serializer_class = SightingListSerializer
    permission_classes = [IsAnyAuthenticatedRole]

    def get_queryset(self):
        user = self.request.user
        qs = SightingReport.objects.select_related("top_match_bike", "top_match_bike__owner", "sighter")
        if user.is_authority or user.is_admin:
            return qs
        if user.is_owner:
            # Owner can retrieve sightings they submitted OR sightings of their bikes
            return qs.filter(
                Q(sighter=user) | Q(top_match_bike__owner=user)
            )
        # Community can only retrieve their own submissions.
        return qs.filter(sighter=user)


@api_view(["PUT"])
@permission_classes([IsAuthorityOrAdmin])
def verify_sighting(request, pk):
    """
    PUT /api/sightings/{id}/verify/
    Authority confirms sighting matches a stolen bike.
    Sets is_verified=True, links bike_id, notifies bike owner.
    """
    sighting = get_object_or_none(SightingReport.objects.all(), pk=pk)
    if sighting is None:
        return error_response(NOT_FOUND_ERROR, status.HTTP_404_NOT_FOUND)

    if request.user.is_authority:
        if not request.user.city:
            return error_response(NO_CITY_ERROR, status.HTTP_403_FORBIDDEN)
        if not cities_match(sighting.sighting_city, request.user.city):
            return error_response(
                "You can only verify sightings in your assigned city.",
                status.HTTP_403_FORBIDDEN,
            )

    bike_id = request.data.get("bike_id")
    if not bike_id:
        return error_response(
            "bike_id is required to verify a sighting.", status.HTTP_400_BAD_REQUEST
        )

    bike = get_object_or_none(Bike.objects.all(), pk=bike_id)
    if bike is None:
        return error_response("Bike not found.", status.HTTP_404_NOT_FOUND)

    sighting.bike = bike
    sighting.is_verified = True
    sighting.verified_by = request.user
    sighting.save(update_fields=["bike", "is_verified", "verified_by"])

    run_in_background(_notify_sighting_verified, sighting)

    return Response({
        "id": sighting.id,
        "is_verified": True,
        "bike_id": bike_id,
        "message": "Sighting verified. Bike owner has been notified.",
    })


@api_view(["PUT"])
@permission_classes([IsOwner])
def owner_confirm_sighting(request, pk):
    """
    PUT /api/sightings/{id}/owner-confirm/
    Owner (of top_match_bike) replies: Yes / No / Not Sure
    """
    sighting = get_object_or_none(SightingReport.objects.all(), pk=pk)
    if sighting is None:
        return error_response(NOT_FOUND_ERROR, status.HTTP_404_NOT_FOUND)

    if not sighting.top_match_bike:
        return error_response(
            "No top match available for this sighting.", status.HTTP_400_BAD_REQUEST
        )

    # Deliberately 404, not 403: a non-owner must not learn the sighting exists.
    if request.user != sighting.top_match_bike.owner:
        return error_response(NOT_FOUND_ERROR, status.HTTP_404_NOT_FOUND)

    # Block duplicate definitive responses
    if sighting.owner_confirmation_status in ("yes", "no"):
        return error_response(
            "You have already responded to this sighting.", status.HTTP_400_BAD_REQUEST
        )

    resp = (request.data.get("response") or "").lower()
    if resp not in ("yes", "no", "not_sure"):
        return error_response(
            "Invalid response. Must be 'yes', 'no', or 'not_sure'.",
            status.HTTP_400_BAD_REQUEST,
        )

    from apps.notifications.notification_service import notify_owner_response
    try:
        notify_owner_response(sighting, resp, request.user)
    except Exception as exc:
        logger.error("Failed to handle owner response: %s", exc)
        return error_response(
            "Failed to record response.", status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return Response({"message": "Response recorded."})


# ─── Notification helpers ──────────────────────────────────────────────────────

_notify_sighting_submitted = deferred_task(
    "apps.notifications.notification_service", "notify_sighting_submitted_extended",
    "Failed to send sighting submitted notification: %s",
)

_notify_sighting_verified = deferred_task(
    "apps.notifications.notification_service", "notify_sighting_verified",
    "Failed to send sighting verified notification: %s",
)
