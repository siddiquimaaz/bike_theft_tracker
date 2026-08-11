"""
apps/reports/serializers.py
Serializers for TheftReport and RecoveryRecord.
Strict field-level validation enforced before view layer.
"""
from datetime import date
from django.conf import settings
from django.contrib.gis.geos import Point
from rest_framework import serializers

from apps.common.uploads import save_uploads
from .models import TheftReport, RecoveryRecord


class TheftReportCreateSerializer(serializers.ModelSerializer):
    reference_number = serializers.ReadOnlyField()
    latitude = serializers.FloatField(required=False, write_only=True)
    longitude = serializers.FloatField(required=False, write_only=True)

    class Meta:
        model = TheftReport
        fields = [
            "bike", "theft_date", "theft_city",
            "latitude", "longitude", "theft_location_detail",
            "fir_number", "description", "reference_number",
        ]

    def validate_bike(self, bike):
        user = self.context["request"].user
        if bike.owner != user:
            raise serializers.ValidationError("You can only report theft of your own bike.")
        if bike.deleted_at is not None:
            raise serializers.ValidationError("Cannot file a report for a deleted bike.")
        if bike.is_stolen:
            raise serializers.ValidationError(
                "This bike already has an active theft report."
            )
        return bike

    def validate_theft_date(self, value):
        if value > date.today():
            raise serializers.ValidationError("Theft date cannot be in the future.")
        return value

    def validate_latitude(self, value):
        if value is not None and not (-90 <= value <= 90):
            raise serializers.ValidationError("Latitude must be between -90 and 90.")
        return value

    def validate_longitude(self, value):
        if value is not None and not (-180 <= value <= 180):
            raise serializers.ValidationError("Longitude must be between -180 and 180.")
        return value

    def create(self, validated_data):
        lat = validated_data.pop("latitude", None)
        lng = validated_data.pop("longitude", None)
        if lat is not None and lng is not None:
            validated_data["theft_location"] = Point(lng, lat, srid=4326)
        return TheftReport.objects.create(**validated_data)


class TheftReportListSerializer(serializers.ModelSerializer):
    reference_number = serializers.CharField(read_only=True)
    bike_info = serializers.SerializerMethodField()
    has_recovery = serializers.SerializerMethodField()

    class Meta:
        model = TheftReport
        fields = [
            "id", "reference_number", "bike_info", "theft_date",
            "theft_city", "fir_number", "status", "has_recovery",
            "owner_recovery_confirmed", "owner_recovery_confirmed_at",
            "created_at", "updated_at",
        ]

    def get_bike_info(self, obj):
        return {
            "id": obj.bike_id,
            "make": obj.bike.make,
            "model": obj.bike.model,
            "year": obj.bike.year,
            "color": obj.bike.color,
            "engine_number": obj.bike.engine_number,
        }

    def get_has_recovery(self, obj):
        return hasattr(obj, "recovery")


class TheftReportDetailSerializer(TheftReportListSerializer):
    theft_latitude = serializers.SerializerMethodField()
    theft_longitude = serializers.SerializerMethodField()
    recovery = serializers.SerializerMethodField()
    timeline = serializers.SerializerMethodField()

    class Meta(TheftReportListSerializer.Meta):
        fields = TheftReportListSerializer.Meta.fields + [
            "theft_latitude", "theft_longitude",
            "theft_location_detail", "description",
            "recovery", "timeline",
        ]

    def get_theft_latitude(self, obj):
        return obj.theft_location.y if obj.theft_location else None

    def get_theft_longitude(self, obj):
        return obj.theft_location.x if obj.theft_location else None

    def get_recovery(self, obj):
        if hasattr(obj, "recovery"):
            return RecoveryRecordSerializer(obj.recovery).data
        return None

    def get_timeline(self, obj):
        events = obj.timeline.select_related("actor").order_by("created_at")
        return [
            {
                "id": event.id,
                "action": event.action,
                "created_at": event.created_at,
                "metadata": event.metadata or {},
                "actor_name": event.actor.full_name if event.actor else None,
            }
            for event in events
        ]


class CommunityTheftFeedSerializer(serializers.ModelSerializer):
    reference_number = serializers.CharField(read_only=True)
    bike_info = serializers.SerializerMethodField()

    class Meta:
        model = TheftReport
        fields = [
            "id",
            "reference_number",
            "status",
            "theft_city",
            "theft_date",
            "theft_location_detail",
            "created_at",
            "bike_info",
        ]

    def get_bike_info(self, obj):
        return {
            "make": obj.bike.make,
            "model": obj.bike.model,
            "color": obj.bike.color,
        }


class StatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=TheftReport.Status.choices)
    note = serializers.CharField(required=False, allow_blank=True)


class RecoveryRecordSerializer(serializers.ModelSerializer):
    recovery_latitude = serializers.SerializerMethodField()
    recovery_longitude = serializers.SerializerMethodField()

    class Meta:
        model = RecoveryRecord
        fields = [
            "id", "theft_report_id", "logged_by_id",
            "fuzzy_match_score", "recovery_date", "recovery_city",
            "recovery_latitude", "recovery_longitude",
            "recovery_location_detail", "bike_condition",
            "notes", "evidence_photos", "created_at",
        ]

    def get_recovery_latitude(self, obj):
        return obj.recovery_location.y if obj.recovery_location else None

    def get_recovery_longitude(self, obj):
        return obj.recovery_location.x if obj.recovery_location else None


class RecoveryCreateSerializer(serializers.ModelSerializer):
    latitude = serializers.FloatField(required=False, write_only=True)
    longitude = serializers.FloatField(required=False, write_only=True)
    evidence_photos = serializers.ListField(
        child=serializers.ImageField(), required=False, max_length=5,
        write_only=True,
    )

    class Meta:
        model = RecoveryRecord
        fields = [
            "fuzzy_match_score", "recovery_date", "recovery_city",
            "latitude", "longitude", "recovery_location_detail",
            "bike_condition", "notes", "evidence_photos",
        ]

    def validate_evidence_photos(self, photos):
        import magic as magic_lib
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        for photo in photos:
            if photo.size > max_bytes:
                raise serializers.ValidationError(
                    f"Each photo must be under {settings.MAX_UPLOAD_SIZE_MB}MB."
                )
            chunk = photo.read(2048)
            photo.seek(0)
            mime = magic_lib.from_buffer(chunk, mime=True)
            if mime not in ("image/jpeg", "image/png"):
                raise serializers.ValidationError("Only JPEG and PNG evidence photos are accepted.")
        return photos

    def create(self, validated_data):
        lat = validated_data.pop("latitude", None)
        lng = validated_data.pop("longitude", None)
        photos = validated_data.pop("evidence_photos", [])

        if lat is not None and lng is not None:
            validated_data["recovery_location"] = Point(lng, lat, srid=4326)

        validated_data["evidence_photos"] = save_uploads(photos, "evidence")
        return RecoveryRecord.objects.create(**validated_data)

    def update(self, instance, validated_data):
        lat = validated_data.pop("latitude", None)
        lng = validated_data.pop("longitude", None)
        photos = validated_data.pop("evidence_photos", None)

        if lat is not None and lng is not None:
            validated_data["recovery_location"] = Point(lng, lat, srid=4326)

        if photos is not None:
            validated_data["evidence_photos"] = save_uploads(photos, "evidence")

        return super().update(instance, validated_data)
