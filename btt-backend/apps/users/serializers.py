"""
apps/users/serializers.py
DRF serializers for user registration, auth, and admin management.
All fields validated before reaching view layer.
"""
import re
from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()

CNIC_PATTERN = re.compile(r"^\d{13}$")
PHONE_PATTERN = re.compile(r"^\+92\d{10}$|^0\d{10}$")


def _normalize_city(value):
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "full_name", "email", "phone", "cnic",
            "role", "city", "password", "confirm_password",
        ]
        extra_kwargs = {
            "role": {"required": False},
        }

    def validate_role(self, value):
        # Registration endpoint only allows owner or community
        if value not in (User.Role.OWNER, User.Role.COMMUNITY):
            raise serializers.ValidationError(
                "Self-registration is only available for 'owner' or 'community' roles."
            )
        return value

    def validate_cnic(self, value):
        if value and not CNIC_PATTERN.match(value):
            raise serializers.ValidationError("CNIC must be exactly 13 digits.")
        return value

    def validate_phone(self, value):
        if value and not PHONE_PATTERN.match(value):
            raise serializers.ValidationError(
                "Phone must be a valid Pakistani number (e.g. +923001234567 or 03001234567)."
            )
        return value

    def validate_city(self, value):
        return _normalize_city(value)

    def validate(self, data):
        for nullable in ("cnic", "phone", "city"):
            if data.get(nullable) == "":
                data[nullable] = None
        if data["password"] != data.pop("confirm_password"):
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return data

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class AuthorityCreationSerializer(serializers.ModelSerializer):
    """Admin creates authority accounts — requires badge_number and CNIC."""
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = [
            "full_name", "email", "phone", "cnic",
            "badge_number", "city", "password",
        ]

    def validate_cnic(self, value):
        if not CNIC_PATTERN.match(value):
            raise serializers.ValidationError("CNIC must be exactly 13 digits.")
        return value

    def validate_badge_number(self, value):
        if not value:
            raise serializers.ValidationError("Badge number is required for authority accounts.")
        return value

    def validate_city(self, value):
        return _normalize_city(value)

    def create(self, validated_data):
        return User.objects.create_user(
            role=User.Role.AUTHORITY,
            is_verified=True,  # Admin-created accounts skip email verification
            **validated_data
        )


class UserListSerializer(serializers.ModelSerializer):
    """Compact representation for admin user list."""
    class Meta:
        model = User
        fields = [
            "id", "full_name", "email", "role", "city",
            "is_verified", "is_active", "created_at",
        ]


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    new_password = serializers.CharField(min_length=8)
    confirm_password = serializers.CharField()

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return data


class UserStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["is_active", "role"]
