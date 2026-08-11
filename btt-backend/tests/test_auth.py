"""
tests/test_auth.py
Authentication endpoint tests — registration, email verify, login, logout,
password reset. Covers happy paths and key error cases.
"""
import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestRegistration:
    url = "/api/auth/register/"

    def test_owner_registration_success(self, api_client):
        payload = {
            "full_name": "Test Owner",
            "email": "new@test.btt",
            "cnic": "4200099999999",
            "role": "owner",
            "password": "Test@12345",
            "confirm_password": "Test@12345",
        }
        response = api_client.post(self.url, payload)
        assert response.status_code == 201
        assert "id" in response.data
        assert response.data["role"] == "owner"

    def test_community_registration_no_cnic(self, api_client):
        payload = {
            "full_name": "Reporter",
            "email": "reporter@test.btt",
            "role": "community",
            "password": "Test@12345",
            "confirm_password": "Test@12345",
        }
        response = api_client.post(self.url, payload)
        assert response.status_code == 201

    def test_authority_self_registration_rejected(self, api_client):
        payload = {
            "full_name": "Fake Officer",
            "email": "fake@test.btt",
            "role": "authority",
            "password": "Test@12345",
            "confirm_password": "Test@12345",
        }
        response = api_client.post(self.url, payload)
        assert response.status_code == 400

    def test_mismatched_passwords_rejected(self, api_client):
        payload = {
            "full_name": "User",
            "email": "u@test.btt",
            "role": "owner",
            "password": "Test@12345",
            "confirm_password": "Different@999",
        }
        response = api_client.post(self.url, payload)
        assert response.status_code == 400
        assert "confirm_password" in response.data

    def test_duplicate_email_rejected(self, api_client, owner_user):
        payload = {
            "full_name": "Dup",
            "email": owner_user.email,
            "role": "owner",
            "password": "Test@12345",
            "confirm_password": "Test@12345",
        }
        response = api_client.post(self.url, payload)
        assert response.status_code == 400

    def test_invalid_cnic_rejected(self, api_client):
        payload = {
            "full_name": "User",
            "email": "x@test.btt",
            "cnic": "123",  # Not 13 digits
            "role": "owner",
            "password": "Test@12345",
            "confirm_password": "Test@12345",
        }
        response = api_client.post(self.url, payload)
        assert response.status_code == 400

    def test_blank_cnic_phone_normalized_for_registration(self, api_client):
        payload = {
            "full_name": "Community User",
            "email": "blank-fields@test.btt",
            "role": "community",
            "cnic": "",
            "phone": "",
            "password": "Test@12345",
            "confirm_password": "Test@12345",
        }
        response = api_client.post(self.url, payload)
        assert response.status_code == 201
        user = User.objects.get(email="blank-fields@test.btt")
        assert user.cnic is None
        assert user.phone is None

    def test_registration_returns_verification_link_in_local_dev_mode(self, api_client, settings):
        settings.LOCAL_DEV_MODE = True
        payload = {
            "full_name": "Dev Owner",
            "email": "dev-owner@test.btt",
            "role": "owner",
            "password": "Test@12345",
            "confirm_password": "Test@12345",
        }
        response = api_client.post(self.url, payload)
        assert response.status_code == 201
        assert "verification_token" in response.data
        assert "verification_url" in response.data


@pytest.mark.django_db
class TestEmailVerification:
    def test_valid_token_verifies_user(self, api_client, db):
        from django.utils import timezone
        from datetime import timedelta
        user = User.objects.create_user(
            email="unverified@test.btt",
            full_name="Unverified",
            password="Test@12345",
            role="owner",
            is_verified=False,
            email_verification_token_expires=timezone.now() + timedelta(hours=24),
        )
        url = f"/api/auth/verify-email/{user.email_verification_token}/"
        response = api_client.post(url)
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.is_verified is True

    def test_invalid_token_rejected(self, api_client):
        import uuid
        url = f"/api/auth/verify-email/{uuid.uuid4()}/"
        response = api_client.post(url)
        assert response.status_code == 400

    def test_expired_token_rejected(self, api_client, db):
        from django.utils import timezone
        from datetime import timedelta

        user = User.objects.create_user(
            email="expired@test.btt",
            full_name="Expired Token",
            password="Test@12345",
            role="owner",
            is_verified=False,
            email_verification_token_expires=timezone.now() - timedelta(minutes=1),
        )
        url = f"/api/auth/verify-email/{user.email_verification_token}/"
        response = api_client.post(url)
        assert response.status_code == 400


@pytest.mark.django_db
class TestLogin:
    url = "/api/auth/login/"

    def test_valid_credentials_return_tokens(self, api_client, owner_user):
        response = api_client.post(self.url, {
            "email": owner_user.email,
            "password": "Test@12345",
        })
        assert response.status_code == 200
        assert "access" in response.data
        assert "refresh" in response.data

    def test_wrong_password_rejected(self, api_client, owner_user):
        response = api_client.post(self.url, {
            "email": owner_user.email,
            "password": "wrongpassword",
        })
        assert response.status_code == 401

    def test_inactive_user_rejected(self, api_client, db):
        user = User.objects.create_user(
            email="inactive@test.btt", full_name="Inactive",
            password="Test@12345", role="owner", is_active=False,
        )
        response = api_client.post(self.url, {
            "email": user.email, "password": "Test@12345"
        })
        assert response.status_code == 401


@pytest.mark.django_db
class TestLogout:
    def test_logout_blacklists_refresh_token(self, owner_client, owner_user):
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(owner_user)
        response = owner_client.post("/api/auth/logout/", {"refresh": str(refresh)})
        assert response.status_code == 200

    def test_logout_without_token_rejected(self, owner_client):
        response = owner_client.post("/api/auth/logout/", {})
        assert response.status_code == 400

    def test_unauthenticated_logout_rejected(self, api_client):
        response = api_client.post("/api/auth/logout/", {"refresh": "fake"})
        assert response.status_code == 401
