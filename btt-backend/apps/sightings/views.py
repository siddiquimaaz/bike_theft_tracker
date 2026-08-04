"""
apps/sightings/views.py
Community sighting submission — auto-runs fuzzy match on POST.
Authority verifies sightings, which notifies the bike owner.
"""
import logging
from django.contrib.gis.geos import Point
from django.db.models import Q
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import serializers

from apps.common.background import background_task, run_in_background
from apps.common.city import cities_match
from apps.common.uploads import save_upload
from apps.users.permissions import IsAnyAuthenticatedRole, IsAuthorityOrAdmin, IsOwner
from .models import SightingReport

logger = logging.getLogger(__name__)

NOT_FOUND_ERROR = "Sighting not found."


# ─── Serializers ──────────────────────────────────────────────────────────────

class SightingCreateSerializer(serializers.ModelSerializer):
    latitude = serializers.FloatField(required=False, write_only=True)
    longitude = serializers.FloatField(required=False, write_only=True)
    photo = serializers.ImageField(required=False, write_only=True)

    class Meta:
        model = SightingReport
        fields = [
            "raw_engine_number", "raw_chassis_number",
            "sighting_date", "sighting_city", "sighting_description",
            "latitude", "longitude", "photo",
        ]

    def create(self, validated_data):
        lat = validated_data.pop("latitude", None)
        lng = validated_data.pop("longitude", None)
        photo = validated_data.pop("photo", None)

        if lat is not None and lng is not None:
            validated_data["sighting_location"] = Point(lng, lat, srid=4326)

        if photo:
            validated_data["photo_url"] = save_upload(photo, "sightings")

        sighting = SightingReport(**validated_data)

        # Auto-run fuzzy match before saving
        query = validated_data.get("raw_engine_number") or validated_data.get("raw_chassis_number")
        if query:
            field = "engine_number" if validated_data.get("raw_engine_number") else "chassis_number"
            from apps.ml.fuzzy_match import find_fuzzy_matches
            matches = find_fuzzy_matches(query, field=field, limit=1)
            if matches:
                best = matches[0]
                sighting.fuzzy_match_score = best["score"]
                try:
                    sighting.top_match_bike_id = int(best["bike_id"])
                except (ValueError, KeyError):
                    pass

        sighting.save()
        return sighting


class SightingListSerializer(serializers.ModelSerializer):
    top_match_info = serializers.SerializerMethodField()
    sighting_latitude = serializers.SerializerMethodField()
    sighting_longitude = serializers.SerializerMethodField()
    # True when the requesting owner is the owner of the matched bike
    # (i.e. this is a sighting OF their bike, not BY them)
    is_about_my_bike = serializers.SerializerMethodField()

    class Meta:
        model = SightingReport
        fields = [
            "id", "raw_engine_number", "raw_chassis_number",
            "fuzzy_match_score", "top_match_info",
            "sighting_date", "sighting_city",
            "sighting_latitude", "sighting_longitude",
            "sighting_description", "photo_url",
            "is_verified", "verified_by_id",
            "owner_confirmation_status", "owner_response_deadline",
            "auto_escalated", "is_archived",
            "is_about_my_bike",
            "created_at",
        ]

    def get_top_match_info(self, obj):
        if not obj.top_match_bike:
            return None
        b = obj.top_match_bike
        return {
            "bike_id": b.id,
            "make": b.make,
            "model": b.model,
            "year": b.year,
            "engine_number": b.engine_number,
        }

    def get_sighting_latitude(self, obj):
        return obj.sighting_location.y if obj.sighting_location else None

    def get_sighting_longitude(self, obj):
        return obj.sighting_location.x if obj.sighting_location else None

    def get_is_about_my_bike(self, obj):
        request = self.context.get("request")
        if not request or not obj.top_match_bike:
            return False
        return obj.top_match_bike.owner_id == request.user.id


# ─── Views ────────────────────────────────────────────────────────────────────

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
    try:
        sighting = SightingReport.objects.get(pk=pk)
    except SightingReport.DoesNotExist:
        return Response({"error": NOT_FOUND_ERROR}, status=status.HTTP_404_NOT_FOUND)

    if request.user.is_authority:
        if not request.user.city:
            return Response(
                {"error": "Your account has no city configured. Contact an admin."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not cities_match(sighting.sighting_city, request.user.city):
            return Response(
                {"error": "You can only verify sightings in your assigned city."},
                status=status.HTTP_403_FORBIDDEN,
            )

    bike_id = request.data.get("bike_id")
    if not bike_id:
        return Response({"error": "bike_id is required to verify a sighting."}, status=status.HTTP_400_BAD_REQUEST)

    from apps.bikes.models import Bike
    try:
        bike = Bike.objects.get(pk=bike_id)
    except Bike.DoesNotExist:
        return Response({"error": "Bike not found."}, status=status.HTTP_404_NOT_FOUND)

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
    try:
        sighting = SightingReport.objects.get(pk=pk)
    except SightingReport.DoesNotExist:
        return Response({"error": NOT_FOUND_ERROR}, status=status.HTTP_404_NOT_FOUND)

    if not sighting.top_match_bike:
        return Response({"error": "No top match available for this sighting."}, status=status.HTTP_400_BAD_REQUEST)

    # Deliberately 404, not 403: a non-owner must not learn the sighting exists.
    if request.user != sighting.top_match_bike.owner:
        return Response({"error": NOT_FOUND_ERROR}, status=status.HTTP_404_NOT_FOUND)

    # Block duplicate definitive responses
    if sighting.owner_confirmation_status in ("yes", "no"):
        return Response(
            {"error": "You have already responded to this sighting."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    resp = (request.data.get("response") or "").lower()
    if resp not in ("yes", "no", "not_sure"):
        return Response({"error": "Invalid response. Must be 'yes', 'no', or 'not_sure'."}, status=status.HTTP_400_BAD_REQUEST)

    from apps.notifications.notification_service import notify_owner_response
    try:
        notify_owner_response(sighting, resp, request.user)
    except Exception as exc:
        logger.error("Failed to handle owner response: %s", exc)
        return Response({"error": "Failed to record response."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response({"message": "Response recorded."})


# ─── Notification helpers ──────────────────────────────────────────────────────

@background_task("Failed to send sighting submitted notification: %s")
def _notify_sighting_submitted(sighting):
    from apps.notifications.notification_service import notify_sighting_submitted_extended
    notify_sighting_submitted_extended(sighting)


@background_task("Failed to send sighting verified notification: %s")
def _notify_sighting_verified(sighting):
    from apps.notifications.notification_service import notify_sighting_verified
    notify_sighting_verified(sighting)
