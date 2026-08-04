"""
apps/bikes/serializers.py
Bike registration and detail serializers.
Engine and chassis numbers are immutable after creation.
"""
import magic
from django.conf import settings
from rest_framework import serializers

from apps.common.uploads import save_upload
from .models import Bike


class BikeCreateSerializer(serializers.ModelSerializer):
    photo = serializers.ImageField(write_only=True, required=False)

    class Meta:
        model = Bike
        fields = [
            "id", "make", "model", "year", "color",
            "registration_number", "registration_city",
            "engine_number", "chassis_number", "photo",
        ]

    def validate_year(self, value):
        if value < 1900 or value > 2100:
            raise serializers.ValidationError("Invalid manufacturing year.")
        return value

    def validate_engine_number(self, value):
        return value.upper().strip()

    def validate_chassis_number(self, value):
        return value.upper().strip()

    def validate_photo(self, photo):
        if photo:
            max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
            if photo.size > max_bytes:
                raise serializers.ValidationError(
                    f"Photo must not exceed {settings.MAX_UPLOAD_SIZE_MB}MB."
                )
            # MIME type check — not just extension
            file_bytes = photo.read(2048)
            photo.seek(0)
            mime = magic.from_buffer(file_bytes, mime=True)
            if mime not in ("image/jpeg", "image/png"):
                raise serializers.ValidationError("Only JPEG and PNG images are accepted.")
        return photo

    def create(self, validated_data):
        photo = validated_data.pop("photo", None)
        bike = Bike(**validated_data)
        if photo:
            bike.photo_url = save_upload(photo, "bikes")
        bike.save()
        return bike


class BikeUpdateSerializer(serializers.ModelSerializer):
    """Color, registration_number, registration_city, and photo can be updated.
    Engine and chassis numbers are IMMUTABLE."""
    photo = serializers.ImageField(write_only=True, required=False)

    class Meta:
        model = Bike
        fields = ["color", "registration_number", "registration_city", "photo"]

    def update(self, instance, validated_data):
        photo = validated_data.pop("photo", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if photo:
            instance.photo_url = save_upload(photo, "bikes")
        instance.save()
        return instance


class BikeListSerializer(serializers.ModelSerializer):
    is_stolen = serializers.BooleanField(read_only=True)
    theft_status = serializers.SerializerMethodField()

    class Meta:
        model = Bike
        fields = [
            "id", "make", "model", "year", "color",
            "engine_number", "chassis_number",
            "registration_number", "registration_city",
            "photo_url", "is_stolen", "theft_status", "created_at",
        ]

    def get_theft_status(self, obj):
        report = obj.active_theft_report
        if report:
            return {"report_id": report.id, "status": report.status}
        return None


class BikeDetailSerializer(BikeListSerializer):
    """Full details including active theft report."""
    class Meta(BikeListSerializer.Meta):
        fields = BikeListSerializer.Meta.fields + ["owner_id"]
