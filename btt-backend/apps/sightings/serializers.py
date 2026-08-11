"""
apps/sightings/serializers.py
Sighting submission and read serializers.

Submission runs the fuzzy match against stolen engine/chassis numbers before the
row is saved, so a sighting arrives already carrying its best candidate bike and
confidence score — the authority queue can then be ordered by confidence without
a second pass.
"""
from django.contrib.gis.geos import Point
from rest_framework import serializers

from apps.common.uploads import save_upload
from .models import SightingReport


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
