from datetime import date, timedelta

import pytest
from django.utils import timezone

from apps.notifications.models import Notification
from apps.notifications.notification_service import (
    auto_escalate_pending_owner_responses,
    notify_case_closed_to_contributors,
    notify_owner_response,
    notify_sighting_submitted_extended,
)
from apps.reports.models import TheftReport, RecoveryRecord, CaseTimeline
from apps.sightings.models import SightingReport


@pytest.mark.django_db
def test_owner_confirm_recovery_closes_case(owner_client, authority_user, sample_report):
    sample_report.status = TheftReport.Status.ACTIVE_INVESTIGATION
    sample_report.save(update_fields=["status"])
    RecoveryRecord.objects.create(
        theft_report=sample_report,
        logged_by=authority_user,
        recovery_date=date.today(),
        recovery_city="Karachi",
        bike_condition="good",
    )
    sample_report.status = TheftReport.Status.PENDING_VERIFICATION
    sample_report.save(update_fields=["status"])

    response = owner_client.put(f"/api/reports/{sample_report.id}/recovery/confirm/", {})
    assert response.status_code == 200
    sample_report.refresh_from_db()
    assert sample_report.status == TheftReport.Status.CLOSED
    assert sample_report.owner_recovery_confirmed is True


@pytest.mark.django_db
def test_owner_confirm_recovery_updates_transition_audit_fields(owner_client, authority_user, sample_report):
    sample_report.status = TheftReport.Status.ACTIVE_INVESTIGATION
    sample_report.authority_last_action_at = timezone.now() - timedelta(days=2)
    sample_report.save(update_fields=["status", "authority_last_action_at"])
    prev_action_ts = sample_report.authority_last_action_at

    RecoveryRecord.objects.create(
        theft_report=sample_report,
        logged_by=authority_user,
        recovery_date=date.today(),
        recovery_city="Karachi",
        bike_condition="good",
    )
    sample_report.status = TheftReport.Status.PENDING_VERIFICATION
    sample_report.save(update_fields=["status"])

    response = owner_client.put(f"/api/reports/{sample_report.id}/recovery/confirm/", {})
    assert response.status_code == 200

    sample_report.refresh_from_db()
    assert sample_report.status == TheftReport.Status.CLOSED
    assert sample_report.authority_last_action_at > prev_action_ts

    close_event = CaseTimeline.objects.filter(
        theft_report=sample_report,
        action="owner_confirmed_recovery_receipt",
    ).last()
    assert close_event is not None
    assert close_event.metadata.get("old_status") == TheftReport.Status.PENDING_VERIFICATION
    assert close_event.metadata.get("new_status") == TheftReport.Status.CLOSED


@pytest.mark.django_db
def test_sighting_timeout_auto_escalates(sample_bike, authority_user, community_user):
    sighting = SightingReport.objects.create(
        top_match_bike=sample_bike,
        fuzzy_match_score=80,
        sighter=community_user,
        sighting_date=date.today(),
        sighting_city="Karachi",
        owner_confirmation_status="pending",
        owner_response_deadline=timezone.now() - timedelta(hours=1),
    )

    escalated = auto_escalate_pending_owner_responses()
    assert escalated == 1
    sighting.refresh_from_db()
    assert sighting.auto_escalated is True
    assert Notification.objects.filter(sighting=sighting, type=Notification.Type.URGENT).exists()


# ─────────────────────────────────────────────────────────────────────────────
# Confidence routing — sighting submission branches by score + photo
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_confidence_routing_high(sample_bike, sample_report, owner_user, authority_user, community_user):
    """Photo + high score → owner handshake AND immediate URGENT to authority."""
    sighting = SightingReport.objects.create(
        top_match_bike=sample_bike,
        fuzzy_match_score=92,
        photo_url="evidence.jpg",
        sighter=community_user,
        sighting_date=date.today(),
        sighting_city="Karachi",
    )

    notify_sighting_submitted_extended(sighting)
    sighting.refresh_from_db()

    # Owner is asked for a handshake confirmation
    assert sighting.owner_confirmation_status == "pending"
    assert Notification.objects.filter(
        user=owner_user,
        type=Notification.Type.SIGHTING_OWNER_HANDSHAKE,
        sighting=sighting,
    ).exists()
    # Authority is notified urgently in the same city — no waiting on owner
    assert Notification.objects.filter(
        user=authority_user,
        type=Notification.Type.URGENT,
        sighting=sighting,
    ).exists()


@pytest.mark.django_db
def test_confidence_routing_low(sample_bike, sample_report, owner_user, authority_user, community_user):
    """Description-only + medium score → owner handshake only; authority held."""
    sighting = SightingReport.objects.create(
        top_match_bike=sample_bike,
        fuzzy_match_score=72,        # ≥ owner alert (70), < photo-high (85)
        photo_url="",                 # no photo — keeps confidence "low"
        sighter=community_user,
        sighting_date=date.today(),
        sighting_city="Karachi",
    )

    notify_sighting_submitted_extended(sighting)
    sighting.refresh_from_db()

    # Owner pinged
    assert sighting.owner_confirmation_status == "pending"
    assert Notification.objects.filter(
        user=owner_user,
        type=Notification.Type.SIGHTING_OWNER_HANDSHAKE,
        sighting=sighting,
    ).exists()
    # Authority NOT yet escalated (pending owner confirmation first)
    assert not Notification.objects.filter(
        user=authority_user,
        type=Notification.Type.URGENT,
        sighting=sighting,
    ).exists()


# ─────────────────────────────────────────────────────────────────────────────
# Owner handshake — not_sure leaves the case open for auto-escalation
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_owner_handshake_not_sure(sample_bike, sample_report, owner_user, community_user):
    """`not_sure` keeps sighting open and writes a timeline marker."""
    sighting = SightingReport.objects.create(
        top_match_bike=sample_bike,
        fuzzy_match_score=80,
        photo_url="",
        sighter=community_user,
        sighting_date=date.today(),
        sighting_city="Karachi",
        owner_confirmation_status="pending",
        owner_response_deadline=timezone.now() + timedelta(hours=12),
    )

    notify_owner_response(sighting, "not_sure", owner_user)
    sighting.refresh_from_db()

    # Sighting stays open and visible — not archived
    assert sighting.owner_confirmation_status == "not_sure"
    assert sighting.is_archived is False
    # Owner gets a confirmation receipt
    assert Notification.objects.filter(
        user=owner_user,
        type=Notification.Type.SIGHTING_OWNER_RESPONSE,
        sighting=sighting,
    ).exists()
    # Timeline records the not_sure decision so escalation path is auditable
    assert CaseTimeline.objects.filter(
        theft_report=sample_report, action="owner_not_sure",
    ).exists()


@pytest.mark.django_db
def test_owner_handshake_timeout(sample_bike, sample_report, authority_user, community_user):
    """Past-deadline pending sighting auto-escalates to authority."""
    sighting = SightingReport.objects.create(
        top_match_bike=sample_bike,
        fuzzy_match_score=78,
        photo_url="",
        sighter=community_user,
        sighting_date=date.today(),
        sighting_city="Karachi",
        owner_confirmation_status="pending",
        owner_response_deadline=timezone.now() - timedelta(hours=2),  # already late
    )

    escalated = auto_escalate_pending_owner_responses()
    assert escalated == 1

    sighting.refresh_from_db()
    assert sighting.auto_escalated is True
    # Authority in the same city receives the URGENT escalation
    assert Notification.objects.filter(
        user=authority_user,
        type=Notification.Type.URGENT,
        sighting=sighting,
    ).exists()
    # And the timeline carries the auto-escalation event
    assert CaseTimeline.objects.filter(
        theft_report=sample_report, action="owner_timeout_auto_escalation",
    ).exists()


# ─────────────────────────────────────────────────────────────────────────────
# Closure broadcast — only contributing community sighters get the thank-you
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_contributor_closure_notification(
    sample_bike, sample_report, community_user, owner_user, authority_user,
):
    """notify_case_closed_to_contributors pings sighters, no one else."""
    SightingReport.objects.create(
        top_match_bike=sample_bike,
        fuzzy_match_score=80,
        sighter=community_user,
        sighting_date=date.today(),
        sighting_city="Karachi",
    )

    notify_case_closed_to_contributors(sample_report)

    # Contributing community user receives the closure broadcast
    assert Notification.objects.filter(
        user=community_user,
        type=Notification.Type.COMMUNITY_CLOSURE,
        report=sample_report,
    ).exists()
    # Owner and authority do NOT receive a community-closure notice
    assert not Notification.objects.filter(
        user=owner_user, type=Notification.Type.COMMUNITY_CLOSURE,
    ).exists()
    assert not Notification.objects.filter(
        user=authority_user, type=Notification.Type.COMMUNITY_CLOSURE,
    ).exists()
    # Timeline records the broadcast for audit
    assert CaseTimeline.objects.filter(
        theft_report=sample_report, action="contributors_notified",
    ).exists()


# ─────────────────────────────────────────────────────────────────────────────
# Timeline coverage — all key transitions write a CaseTimeline row
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_timeline_events_generated(
    sample_bike, sample_report, owner_user, authority_user, community_user,
):
    """A representative sighting flow leaves a complete timeline trail."""
    sighting = SightingReport.objects.create(
        top_match_bike=sample_bike,
        fuzzy_match_score=88,
        photo_url="evidence.jpg",
        sighter=community_user,
        sighting_date=date.today(),
        sighting_city="Karachi",
    )

    # Three transitions, three timeline events expected.
    notify_sighting_submitted_extended(sighting)        # → sighting_submitted + owner_handshake_sent
    notify_owner_response(sighting, "yes", owner_user)  # → owner_confirmed_sighting
    notify_case_closed_to_contributors(sample_report)   # → contributors_notified

    actions_logged = set(
        CaseTimeline.objects
        .filter(theft_report=sample_report)
        .values_list("action", flat=True)
    )
    expected = {
        "sighting_submitted",
        "owner_handshake_sent",
        "owner_confirmed_sighting",
        "contributors_notified",
    }
    missing = expected - actions_logged
    assert not missing, f"Missing timeline events: {missing}. Got: {actions_logged}"
