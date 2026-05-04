"""
tests/test_theft_alert_notifications.py

Verifies the city-scoped notification fan-out that fires when a theft report is
submitted.  Covers:

  1. Owner receives THEFT_REPORTED with their own report reference.
  2. Authority in the SAME city receives THEFT_REPORTED.
  3. Authority in a DIFFERENT city does NOT receive any notification.
  4. Community users in the SAME city receive a SYSTEM alert (no owner PII).
  5. Community users in a DIFFERENT city do NOT receive any notification.
  6. Admin role does NOT receive a per-case notification from notify_theft_reported.
  7. Notification message contains bike make/model and reference number.
  8. Community message contains NO owner email or phone (privacy guard).
  9. A 'report_filed' timeline event is created for the case.
 10. Zero notifications when no authority/community users share the theft city.
 11. Multiple authority officers in same city all get notified individually.
 12. Multiple community members in same city all get notified individually.
 13. The bike owner is excluded from the community fan-out even if their
     role were community (belt-and-suspenders check).
 14. End-to-end: POST /api/reports/ triggers the full notification fan-out.
"""

import pytest
from datetime import date

from apps.notifications.models import Notification
from apps.notifications.notification_service import notify_theft_reported
from apps.reports.models import TheftReport, CaseTimeline


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_user(role, email, city="Karachi", **extra):
    """Create a minimal, verified, active user for test isolation."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    kwargs = dict(
        full_name=f"Test {role.title()}",
        email=email,
        role=role,
        is_verified=True,
        is_active=True,
        city=city,
    )
    kwargs.update(extra)
    return User.objects.create_user(password="Test@12345", **kwargs)


def _make_bike(owner):
    from apps.bikes.models import Bike
    return Bike.objects.create(
        owner=owner,
        make="Honda",
        model="CG 125",
        year=2022,
        color="Red",
        engine_number=f"ENG{owner.pk}TEST01",
        chassis_number=f"CHS{owner.pk}TEST01",
        registration_city=owner.city or "Karachi",
    )


def _make_report(bike, owner, theft_city="Karachi"):
    return TheftReport.objects.create(
        bike=bike,
        reported_by=owner,
        theft_date=date.today(),
        theft_city=theft_city,
        status=TheftReport.Status.NEW_CASE,
    )


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def karachi_owner(db):
    return _make_user("owner", "k.owner@btt.test", city="Karachi", cnic="4200099990001")


@pytest.fixture
def karachi_authority(db):
    return _make_user("authority", "k.authority@btt.test", city="Karachi",
                      badge_number="KHI-001", cnic="4200099990002")


@pytest.fixture
def lahore_authority(db):
    return _make_user("authority", "l.authority@btt.test", city="Lahore",
                      badge_number="LHR-001", cnic="4200099990003")


@pytest.fixture
def karachi_community(db):
    return _make_user("community", "k.community@btt.test", city="Karachi")


@pytest.fixture
def lahore_community(db):
    return _make_user("community", "l.community@btt.test", city="Lahore")


@pytest.fixture
def admin_user_2(db):
    return _make_user("admin", "admin2@btt.test", city="Karachi")


@pytest.fixture
def report(db, karachi_owner, karachi_authority, karachi_community, lahore_authority, lahore_community):
    """Create a theft report in Karachi; all role-users already exist in DB."""
    bike = _make_bike(karachi_owner)
    return _make_report(bike, karachi_owner, theft_city="Karachi")


# ─── Core notification fan-out tests ─────────────────────────────────────────

@pytest.mark.django_db
def test_owner_receives_theft_reported_notification(report, karachi_owner):
    notify_theft_reported(report)

    owner_notifs = Notification.objects.filter(
        user=karachi_owner,
        type=Notification.Type.THEFT_REPORTED,
    )
    assert owner_notifs.count() == 1, "Owner should receive exactly one THEFT_REPORTED notification"


@pytest.mark.django_db
def test_same_city_authority_receives_theft_reported(report, karachi_authority):
    notify_theft_reported(report)

    notif = Notification.objects.filter(
        user=karachi_authority,
        type=Notification.Type.THEFT_REPORTED,
    ).first()
    assert notif is not None, "Authority in same city should receive a THEFT_REPORTED notification"


@pytest.mark.django_db
def test_different_city_authority_not_notified(report, lahore_authority):
    notify_theft_reported(report)

    count = Notification.objects.filter(user=lahore_authority).count()
    assert count == 0, "Authority in a different city must NOT receive any notification"


@pytest.mark.django_db
def test_same_city_community_receives_system_notification(report, karachi_community):
    notify_theft_reported(report)

    notif = Notification.objects.filter(
        user=karachi_community,
        type=Notification.Type.SYSTEM,
    ).first()
    assert notif is not None, "Community in same city should receive a SYSTEM notification"


@pytest.mark.django_db
def test_different_city_community_not_notified(report, lahore_community):
    notify_theft_reported(report)

    count = Notification.objects.filter(user=lahore_community).count()
    assert count == 0, "Community in a different city must NOT receive any notification"


@pytest.mark.django_db
def test_city_fanout_normalizes_whitespace_and_case(report, karachi_authority, karachi_community):
    report.theft_city = "  KARACHI  "
    report.save(update_fields=["theft_city"])
    karachi_authority.city = "karachi"
    karachi_authority.save(update_fields=["city"])
    karachi_community.city = "  Karachi"
    karachi_community.save(update_fields=["city"])

    notify_theft_reported(report)

    assert Notification.objects.filter(
        user=karachi_authority,
        type=Notification.Type.THEFT_REPORTED,
    ).exists()
    assert Notification.objects.filter(
        user=karachi_community,
        type=Notification.Type.SYSTEM,
    ).exists()


@pytest.mark.django_db
def test_admin_not_notified_on_theft_report(report, admin_user_2):
    notify_theft_reported(report)

    count = Notification.objects.filter(user=admin_user_2).count()
    assert count == 0, "Admin should NOT receive a notification from notify_theft_reported"


# ─── Message content tests ────────────────────────────────────────────────────

@pytest.mark.django_db
def test_owner_message_contains_reference_and_bike(report, karachi_owner):
    notify_theft_reported(report)

    notif = Notification.objects.filter(
        user=karachi_owner,
        type=Notification.Type.THEFT_REPORTED,
    ).first()
    assert notif is not None
    assert report.reference_number in notif.message
    assert "Honda" in notif.message
    assert "CG 125" in notif.message


@pytest.mark.django_db
def test_authority_message_contains_city_and_reference(report, karachi_authority):
    notify_theft_reported(report)

    notif = Notification.objects.filter(
        user=karachi_authority,
        type=Notification.Type.THEFT_REPORTED,
    ).first()
    assert notif is not None
    assert report.reference_number in notif.message
    assert "Karachi" in notif.message


@pytest.mark.django_db
def test_community_message_contains_make_model_and_city(report, karachi_community):
    notify_theft_reported(report)

    notif = Notification.objects.filter(
        user=karachi_community,
        type=Notification.Type.SYSTEM,
    ).first()
    assert notif is not None
    assert "Honda" in notif.message
    assert "CG 125" in notif.message
    assert "Karachi" in notif.message


@pytest.mark.django_db
def test_community_message_contains_no_owner_pii(report, karachi_owner, karachi_community):
    """Community alert must never expose the owner's email, phone, or CNIC."""
    notify_theft_reported(report)

    notif = Notification.objects.filter(
        user=karachi_community,
        type=Notification.Type.SYSTEM,
    ).first()
    assert notif is not None
    assert karachi_owner.email not in notif.message
    # phone may be None/empty — guard before checking
    if karachi_owner.phone:
        assert karachi_owner.phone not in notif.message
    assert karachi_owner.cnic not in notif.message


# ─── Timeline event test ──────────────────────────────────────────────────────

@pytest.mark.django_db
def test_report_filed_timeline_event_created(report):
    notify_theft_reported(report)

    event = CaseTimeline.objects.filter(
        theft_report=report,
        action="report_filed",
    ).first()
    assert event is not None, "A 'report_filed' timeline event should be created"


# ─── Edge cases ───────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_no_notifications_when_no_city_matches(db):
    """If no authority/community users share the theft city, only owner is notified."""
    owner = _make_user("owner", "solo.owner@btt.test", city="Quetta", cnic="4200099990010")
    bike = _make_bike(owner)
    report = _make_report(bike, owner, theft_city="Quetta")

    # Create users in a different city so nothing matches
    _make_user("authority", "karachi.auth2@btt.test", city="Karachi",
               badge_number="KHI-999", cnic="4200099990011")
    _make_user("community", "karachi.comm2@btt.test", city="Karachi")

    notify_theft_reported(report)

    # Only the owner notification should exist
    all_notifs = Notification.objects.filter(report=report)
    assert all_notifs.count() == 1
    assert all_notifs.first().user == owner


@pytest.mark.django_db
def test_multiple_authority_officers_all_notified(db):
    """All authority users in the theft city receive individual notifications."""
    owner = _make_user("owner", "multi.owner@btt.test", city="Karachi", cnic="4200099991000")
    bike = _make_bike(owner)
    report = _make_report(bike, owner, theft_city="Karachi")

    officers = [
        _make_user("authority", f"officer{i}@btt.test", city="Karachi",
                   badge_number=f"KHI-{100+i}", cnic=f"420009999100{i+1}")
        for i in range(3)
    ]

    notify_theft_reported(report)

    for officer in officers:
        notif = Notification.objects.filter(
            user=officer,
            type=Notification.Type.THEFT_REPORTED,
        ).first()
        assert notif is not None, f"Officer {officer.email} should have been notified"


@pytest.mark.django_db
def test_multiple_community_members_all_notified(db):
    """All community members in the theft city receive individual notifications."""
    owner = _make_user("owner", "mc.owner@btt.test", city="Karachi", cnic="4200099990030")
    bike = _make_bike(owner)
    report = _make_report(bike, owner, theft_city="Karachi")

    members = [
        _make_user("community", f"member{i}@btt.test", city="Karachi")
        for i in range(3)
    ]

    notify_theft_reported(report)

    for member in members:
        notif = Notification.objects.filter(
            user=member,
            type=Notification.Type.SYSTEM,
        ).first()
        assert notif is not None, f"Community member {member.email} should have been notified"


@pytest.mark.django_db
def test_owner_excluded_from_community_fan_out(db):
    """
    Belt-and-suspenders: if the owner's user ID happens to also appear in the
    community query result (e.g. due to a future role-change scenario), they
    should not receive a duplicate community SYSTEM notification.
    The service's .exclude(id=owner.id) should prevent this.
    """
    owner = _make_user("owner", "excl.owner@btt.test", city="Karachi", cnic="4200099990040")
    community = _make_user("community", "excl.comm@btt.test", city="Karachi")
    bike = _make_bike(owner)
    report = _make_report(bike, owner, theft_city="Karachi")

    notify_theft_reported(report)

    # Owner should get exactly one THEFT_REPORTED notification — not a SYSTEM one
    owner_notifs = Notification.objects.filter(user=owner)
    assert owner_notifs.count() == 1
    assert owner_notifs.first().type == Notification.Type.THEFT_REPORTED

    # Community user gets their SYSTEM notification
    assert Notification.objects.filter(user=community, type=Notification.Type.SYSTEM).exists()


# ─── End-to-end API test ─────────────────────────────────────────────────────

@pytest.mark.django_db
def test_api_file_report_triggers_city_notifications(db):
    """
    POST /api/reports/ (owner filing a report) should trigger the full
    notify_theft_reported fan-out: owner + same-city authority + same-city community.
    """
    from rest_framework.test import APIClient
    from rest_framework_simplejwt.tokens import RefreshToken
    from apps.bikes.models import Bike

    owner = _make_user("owner", "api.owner@btt.test", city="Karachi", cnic="4200099990050")
    authority = _make_user("authority", "api.auth@btt.test", city="Karachi",
                           badge_number="KHI-API", cnic="4200099990051")
    community = _make_user("community", "api.comm@btt.test", city="Karachi")

    bike = Bike.objects.create(
        owner=owner,
        make="Yamaha",
        model="YBR 125",
        year=2021,
        color="Blue",
        engine_number="YMHAPI1234567",
        chassis_number="YMHCHSAPI12345",
        registration_city="Karachi",
    )

    client = APIClient()
    refresh = RefreshToken.for_user(owner)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")

    payload = {
        "bike": bike.id,
        "theft_date": str(date.today()),
        "theft_city": "Karachi",
        "description": "Stolen from parking",
    }
    response = client.post("/api/reports/", payload, format="json")

    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.data}"

    # Owner notification
    assert Notification.objects.filter(
        user=owner, type=Notification.Type.THEFT_REPORTED
    ).exists(), "Owner should have a THEFT_REPORTED notification after filing"

    # Authority in same city
    assert Notification.objects.filter(
        user=authority, type=Notification.Type.THEFT_REPORTED
    ).exists(), "Authority in same city should have been notified"

    # Community in same city
    assert Notification.objects.filter(
        user=community, type=Notification.Type.SYSTEM
    ).exists(), "Community in same city should have been notified"
