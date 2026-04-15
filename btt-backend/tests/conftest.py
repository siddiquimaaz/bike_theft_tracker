"""
tests/conftest.py
Shared pytest fixtures — user factories, authenticated API clients, sample bikes.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


# ─── User Fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def api_client():
    return APIClient()


def _make_user(role, email, extra=None):
    data = dict(
        full_name=f"Test {role.title()}",
        email=email,
        role=role,
        is_verified=True,
        is_active=True,
    )
    if extra:
        data.update(extra)
    user = User.objects.create_user(password="Test@12345", **data)
    return user


@pytest.fixture
def owner_user(db):
    return _make_user("owner", "owner@test.btt", {"cnic": "4200011111110"})


@pytest.fixture
def owner_user_2(db):
    return _make_user("owner", "owner2@test.btt", {"cnic": "4200011111112"})


@pytest.fixture
def authority_user(db):
    return _make_user(
        "authority", "authority@test.btt",
        {"badge_number": "TEST-001", "city": "Karachi", "cnic": "4200011111113"},
    )


@pytest.fixture
def authority_user_lahore(db):
    return _make_user(
        "authority", "authority.lahore@test.btt",
        {"badge_number": "TEST-002", "city": "Lahore", "cnic": "4200011111114"},
    )


@pytest.fixture
def community_user(db):
    return _make_user("community", "community@test.btt")


@pytest.fixture
def admin_user(db):
    return _make_user("admin", "admin@test.btt")


# ─── Authenticated Clients ────────────────────────────────────────────────────

def _auth_client(user):
    from rest_framework_simplejwt.tokens import RefreshToken
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client


@pytest.fixture
def owner_client(owner_user):
    return _auth_client(owner_user)


@pytest.fixture
def authority_client(authority_user):
    return _auth_client(authority_user)


@pytest.fixture
def authority_client_lahore(authority_user_lahore):
    return _auth_client(authority_user_lahore)


@pytest.fixture
def community_client(community_user):
    return _auth_client(community_user)


@pytest.fixture
def admin_client(admin_user):
    return _auth_client(admin_user)


# ─── Bike + Report Fixtures ───────────────────────────────────────────────────

@pytest.fixture
def sample_bike(db, owner_user):
    from apps.bikes.models import Bike
    return Bike.objects.create(
        owner=owner_user,
        make="Honda",
        model="CG 125",
        year=2022,
        color="Black",
        engine_number="HND22A1234567",
        chassis_number="MRHGC1250NY123456",
        registration_city="Karachi",
    )


@pytest.fixture
def sample_report(db, sample_bike, owner_user):
    from apps.reports.models import TheftReport
    from datetime import date
    return TheftReport.objects.create(
        bike=sample_bike,
        reported_by=owner_user,
        theft_date=date.today(),
        theft_city="Karachi",
        status="stolen",
    )


@pytest.fixture
def recovered_report(db, sample_report, authority_user):
    from apps.reports.models import RecoveryRecord
    from datetime import date
    recovery = RecoveryRecord.objects.create(
        theft_report=sample_report,
        logged_by=authority_user,
        recovery_date=date.today(),
        recovery_city="Karachi",
        bike_condition="good",
    )
    sample_report.status = "recovered"
    sample_report.save(update_fields=["status"])
    return sample_report
