import pytest
from datetime import date

from apps.notifications.notification_service import notify_sighting_submitted_extended
from apps.notifications.models import Notification
from apps.sightings.models import SightingReport


@pytest.mark.django_db
def test_high_confidence_photo_triggers_owner_and_authority(sample_bike, owner_user, authority_user, community_user):
    sighting = SightingReport.objects.create(
        top_match_bike=sample_bike,
        fuzzy_match_score=90,
        photo_url="photo.jpg",
        sighter=community_user,
        sighting_date=date.today(),
        sighting_city="Karachi",
    )

    notify_sighting_submitted_extended(sighting)
    sighting.refresh_from_db()

    assert sighting.owner_confirmation_status == "pending"
    assert Notification.objects.filter(user=owner_user, type=Notification.Type.SIGHTING_OWNER_HANDSHAKE, sighting_id=sighting.id).exists()
    assert Notification.objects.filter(type=Notification.Type.URGENT, sighting_id=sighting.id).exists()


@pytest.mark.django_db
def test_low_confidence_only_owner_ping(sample_bike, owner_user, community_user):
    sighting = SightingReport.objects.create(
        top_match_bike=sample_bike,
        fuzzy_match_score=75,
        photo_url="",
        sighter=community_user,
        sighting_date=date.today(),
        sighting_city="Karachi",
    )

    notify_sighting_submitted_extended(sighting)
    sighting.refresh_from_db()

    assert sighting.owner_confirmation_status == "pending"
    assert Notification.objects.filter(user=owner_user, type=Notification.Type.SIGHTING_OWNER_HANDSHAKE, sighting_id=sighting.id).exists()
    # No URGENT notifications should have been created for authority
    assert not Notification.objects.filter(type=Notification.Type.URGENT, sighting_id=sighting.id).exists()


@pytest.mark.django_db
def test_owner_confirm_endpoint_yes_escalates(sample_bike, owner_user, authority_user, owner_client, community_user):
    sighting = SightingReport.objects.create(
        top_match_bike=sample_bike,
        fuzzy_match_score=80,
        photo_url="",
        sighter=community_user,
        sighting_date=date.today(),
        sighting_city="Karachi",
    )

    # Prime the handshake (this simulates the original notification flow)
    notify_sighting_submitted_extended(sighting)

    resp = owner_client.put(f"/api/sightings/{sighting.id}/owner-confirm/", {"response": "yes"}, format="json")
    assert resp.status_code == 200

    sighting.refresh_from_db()
    assert sighting.owner_confirmation_status == "yes"
    # Authority should receive an URGENT notification after owner confirmation
    assert Notification.objects.filter(type=Notification.Type.URGENT, sighting_id=sighting.id).exists()


@pytest.mark.django_db
def test_owner_confirm_endpoint_rejects_non_owner_roles(
    sample_bike, community_user, authority_client, community_client
):
    sighting = SightingReport.objects.create(
        top_match_bike=sample_bike,
        fuzzy_match_score=82,
        photo_url="",
        sighter=community_user,
        sighting_date=date.today(),
        sighting_city="Karachi",
    )

    authority_resp = authority_client.put(
        f"/api/sightings/{sighting.id}/owner-confirm/", {"response": "yes"}, format="json"
    )
    community_resp = community_client.put(
        f"/api/sightings/{sighting.id}/owner-confirm/", {"response": "yes"}, format="json"
    )

    assert authority_resp.status_code == 403
    assert community_resp.status_code == 403
