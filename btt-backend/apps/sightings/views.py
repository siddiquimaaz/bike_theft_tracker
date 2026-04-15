"""
apps/sightings/views.py
Community sighting submission — auto-runs fuzzy match on POST.
Authority verifies sightings, which notifies the bike owner.
"""
import logging
import threading
import uuid
import os
from django.conf import settings
from django.contrib.gis.geos import Point
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import serializers

from apps.users.permissions import IsAnyAuthenticatedRole, IsAuthorityOrAdmin
from .models import SightingReport

logger = logging.getLogger(__name__)


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
            ext = photo.name.rsplit(".", 1)[-1].lower()
            filename = f"{uuid.uuid4()}.{ext}"
            path = os.path.join(settings.MEDIA_ROOT, "sightings", filename)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb+") as dest:
                for chunk in photo.chunks():
                    dest.write(chunk)
            validated_data["photo_url"] = filename

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
                from apps.bikes.models import Bike
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

    class Meta:
        model = SightingReport
        fields = [
            "id", "raw_engine_number", "raw_chassis_number",
            "fuzzy_match_score", "top_match_info",
            "sighting_date", "sighting_city",
            "sighting_latitude", "sighting_longitude",
            "sighting_description", "photo_url",
            "is_verified", "verified_by_id",
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


# ─── Views ────────────────────────────────────────────────────────────────────

class SightingListCreateView(generics.ListCreateAPIView):
    """
    POST /api/sightings/  — Any authenticated user submits sighting
    GET  /api/sightings/  — Authority/Admin see all unverified sightings
    """
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAnyAuthenticatedRole()]
        return [IsAuthorityOrAdmin()]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return SightingCreateSerializer
        return SightingListSerializer

    def get_queryset(self):
        return (
            SightingReport.objects.filter(is_verified=False)
            .select_related("top_match_bike")
            .order_by("-fuzzy_match_score", "-created_at")
        )

    def perform_create(self, serializer):
        sighting = serializer.save(sighter=self.request.user)
        threading.Thread(
            target=_notify_sighting_submitted,
            args=(sighting,),
            daemon=True,
        ).start()


class SightingDetailView(generics.RetrieveAPIView):
    """GET /api/sightings/{id}/ — Full sighting detail with fuzzy match candidate"""
    serializer_class = SightingListSerializer
    permission_classes = [IsAnyAuthenticatedRole]
    queryset = SightingReport.objects.select_related("top_match_bike", "sighter")


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
        return Response({"error": "Sighting not found."}, status=status.HTTP_404_NOT_FOUND)

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

    threading.Thread(
        target=_notify_sighting_verified,
        args=(sighting,),
        daemon=True,
    ).start()

    return Response({
        "id": sighting.id,
        "is_verified": True,
        "bike_id": bike_id,
        "message": "Sighting verified. Bike owner has been notified.",
    })


# ─── Notification helpers ──────────────────────────────────────────────────────

def _notify_sighting_submitted(sighting):
    from apps.notifications.notification_service import notify_sighting_submitted
    try:
        notify_sighting_submitted(sighting)
    except Exception as exc:
        logger.error("Failed to send sighting submitted notification: %s", exc)


def _notify_sighting_verified(sighting):
    from apps.notifications.notification_service import notify_sighting_verified
    try:
        notify_sighting_verified(sighting)
    except Exception as exc:
        logger.error("Failed to send sighting verified notification: %s", exc)
