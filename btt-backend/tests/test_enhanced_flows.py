from datetime import date, timedelta

import pytest
from django.utils import timezone

from apps.notifications.models import Notification
from apps.notifications.notification_service import auto_escalate_pending_owner_responses
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
