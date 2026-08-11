"""
Notification domain workflows and routing logic.
"""
import logging
from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from apps.common.city import filter_by_city
from apps.reports.timeline import add_case_timeline_event
from .models import Notification

logger = logging.getLogger(__name__)


def _active_authorities_in(city):
    """Authority officers on duty in `city`. Empty when the city is blank."""
    from apps.users.models import User
    return filter_by_city(
        User.objects.filter(role=User.Role.AUTHORITY, is_active=True), city
    )


def _open_owner_handshake(sighting, now, response_hours):
    """
    Put a sighting into the 'awaiting owner reply' state and start the clock.
    After the deadline, auto_escalate_pending_owner_responses() takes over.
    """
    sighting.owner_confirmation_status = "pending"
    sighting.owner_notified_at = now
    sighting.owner_response_deadline = now + timedelta(hours=response_hours)
    sighting.save(update_fields=[
        "owner_confirmation_status", "owner_notified_at", "owner_response_deadline",
    ])


def _create_in_app(user, notification_type, message, report=None, sighting=None, metadata=None):
    """Persist an in-app notification."""
    try:
        Notification.objects.create(
            user=user,
            report=report,
            sighting=sighting,
            type=notification_type,
            message=message,
            delivery_channel=Notification.Channel.IN_APP,
            metadata=metadata or {},
        )
    except Exception as exc:
        logger.error("Failed to create in-app notification: %s", exc)


# ─── Trigger: Theft Report Created ────────────────────────────────────────────

def notify_theft_reported(report):
    """
    Fires when a theft report is submitted.

    1. Owner — confirms their report was filed.
    2. Authority users in the same city — case assignment alert.
    3. Community users in the same city — public awareness alert
       (no owner PII, only make/model and reference number).
    """
    from apps.users.models import User

    owner = report.reported_by
    theft_city = report.theft_city or ""

    # 1. Owner confirmation
    _create_in_app(
        owner,
        Notification.Type.THEFT_REPORTED,
        (
            f"Your theft report has been filed. "
            f"Reference: {report.reference_number}. "
            f"Bike: {report.bike.make} {report.bike.model}."
        ),
        report,
    )

    # 2. Authority — same city only
    for officer in _active_authorities_in(theft_city):
        _create_in_app(
            officer,
            Notification.Type.THEFT_REPORTED,
            (
                f"New case in your city: {report.reference_number} — "
                f"{report.bike.make} {report.bike.model} stolen in {theft_city}."
            ),
            report,
        )

    # 3. Community — same city only (no owner contact/PII)
    community_qs = filter_by_city(
        User.objects.filter(role=User.Role.COMMUNITY, is_active=True), theft_city
    ).exclude(id=owner.id)
    for member in community_qs:
        _create_in_app(
            member,
            Notification.Type.SYSTEM,
            (
                f"\U0001f6a8 {report.bike.make} {report.bike.model} reported stolen "
                f"in {theft_city} (Ref: {report.reference_number}). "
                f"Submit a sighting if you spot it."
            ),
        )

    # Add case timeline event
    add_case_timeline_event(report, "report_filed")

    # TODO (future release): send_theft_reported_email(owner, report)
    # Requires EMAIL_HOST_USER + EMAIL_HOST_PASSWORD in .env


# ─── Trigger: Status Changed ──────────────────────────────────────────────────

def notify_status_changed(report, old_status):
    # Keep owner notifications milestone-based to avoid noisy internal updates.
    owner_visible_statuses = {"bike_located", "pending_verification", "recovered"}
    if report.status in owner_visible_statuses:
        owner = report.reported_by
        if report.status in {"pending_verification", "recovered"}:
            # Recovery confirmation states must carry an actionable CTA for owners.
            message = (
                f"Case {report.reference_number} is awaiting your verification. "
                "Confirm bike receipt to close the case."
            )
            _create_in_app(
                owner,
                Notification.Type.RECOVERY,
                message,
                report,
                metadata={"requires_owner_confirmation": True},
            )
        else:
            message = (
                f"Case {report.reference_number} status changed: "
                f"{old_status} → {report.status}."
            )
            _create_in_app(owner, Notification.Type.STATUS_UPDATE, message, report)
    add_case_timeline_event(
        report,
        "status_changed",
        metadata={"old_status": old_status, "new_status": report.status},
    )

    # TODO (future release): send_status_update_email(owner, report, old_status)


# ─── Trigger: Bike Recovered ──────────────────────────────────────────────────

def notify_bike_recovered(report, recovery):
    owner = report.reported_by
    message = (
        f"Your {report.bike.make} {report.bike.model} has been RECOVERED "
        f"in {recovery.recovery_city} on {recovery.recovery_date}. "
        f"Condition: {recovery.bike_condition or 'not specified'}."
    )
    _create_in_app(
        owner,
        Notification.Type.RECOVERY,
        (
            f"{message} Confirm pickup from your dashboard to finalize the case closure."
        ),
        report,
        metadata={"requires_owner_confirmation": True},
    )
    add_case_timeline_event(
        report,
        "bike_marked_recovered",
        actor=recovery.logged_by,
        metadata={"recovery_city": recovery.recovery_city, "recovery_date": str(recovery.recovery_date)},
    )

    # TODO (future release): send_recovery_email(owner, report, recovery)
    # TODO (future release): send_recovery_sms(owner, report, recovery)


# ─── Trigger: Recovery Record Amended ─────────────────────────────────────────

def notify_recovery_amended(report, recovery, officer):
    owner = report.reported_by
    message = (
        f"Recovery details for case {report.reference_number} were updated "
        f"by {officer.full_name}. New condition: {recovery.bike_condition or 'not specified'}."
    )
    _create_in_app(owner, Notification.Type.STATUS_UPDATE, message, report)
    add_case_timeline_event(
        report,
        "recovery_amended",
        actor=officer,
        metadata={"bike_condition": recovery.bike_condition},
    )

    # TODO (future release): send_recovery_amended_email(owner, report, recovery, officer)


# ─── Trigger: Sighting Verified ───────────────────────────────────────────────

def notify_sighting_verified(sighting):
    """Notifies the bike owner when a sighting of their bike is verified."""
    if not sighting.bike:
        return
    owner = sighting.bike.owner
    message = (
        f"URGENT: A verified sighting of your "
        f"{sighting.bike.make} {sighting.bike.model} "
        f"was confirmed in {sighting.sighting_city} on {sighting.sighting_date}."
    )

    # In-app notification
    report = _get_report_for_sighting(sighting)
    _create_in_app(owner, Notification.Type.SIGHTING_MATCHED, message, report=report, sighting=sighting)
    if report:
        add_case_timeline_event(
            report,
            "sighting_verified",
            actor=sighting.verified_by,
            metadata={"sighting_id": sighting.id},
        )

    # TODO (future release): send_sighting_verified_email(owner, sighting)
    # TODO (future release): send_sighting_verified_sms(owner, sighting)


# Enhanced sighting / owner handshake flow
def notify_sighting_submitted_extended(sighting):
    """
    Enhanced flow:
    - Photo + high fuzzy score -> urgent authority alert + owner handshake (owner pinged)
    - Description only / low confidence -> owner handshake only (authority not notified until owner confirms)
    """
    now = timezone.now()
    score = float(sighting.fuzzy_match_score or 0)
    has_photo = bool(sighting.photo_url)
    report = _get_report_for_sighting(sighting)
    add_case_timeline_event(
        report,
        "sighting_submitted",
        actor=sighting.sighter,
        metadata={
            "sighting_id": sighting.id,
            "confidence_score": score,
            "has_photo": has_photo,
        },
    )

    # If there's a top-match bike available, prepare handshake
    if sighting.top_match_bike:
        owner = sighting.top_match_bike.owner
        # Photo + high confidence -> urgent authority + ping owner
        if has_photo and score >= settings.PHOTO_HIGH_CONFIDENCE_THRESHOLD:
            _open_owner_handshake(sighting, now, settings.SIGHTING_OWNER_RESPONSE_HOURS)

            _create_in_app(
                owner,
                Notification.Type.SIGHTING_OWNER_HANDSHAKE,
                f"Is this your {sighting.top_match_bike.make} {sighting.top_match_bike.model} (Reported {sighting.sighting_date})? Reply Yes / No / Not Sure.",
                report=report,
                sighting=sighting,
                metadata={"requires_response": True, "response_options": ["yes", "no", "not_sure"]},
            )

            # Notify authorities urgently
            for officer in _active_authorities_in(sighting.sighting_city or ""):
                _create_in_app(
                    officer,
                    Notification.Type.URGENT,
                    f"URGENT: High-confidence photo sighting in {sighting.sighting_city} ({score:.0f}%). Owner confirmation pending.",
                    report=report,
                    sighting=sighting,
                )
            add_case_timeline_event(report, "owner_handshake_sent", metadata={"sighting_id": sighting.id, "confidence_level": "high"})
            return

        # Low-confidence or description-only: ping owner for confirmation first
        if score >= settings.OWNER_ALERT_THRESHOLD:
            _open_owner_handshake(sighting, now, settings.SIGHTING_OWNER_RESPONSE_HOURS)

            _create_in_app(
                owner,
                Notification.Type.SIGHTING_OWNER_HANDSHAKE,
                f"A community sighting in {sighting.sighting_city} on {sighting.sighting_date} may match your {sighting.top_match_bike.make} {sighting.top_match_bike.model}. Is this your bike? Reply Yes / No / Not Sure.",
                report=report,
                sighting=sighting,
                metadata={"requires_response": True, "response_options": ["yes", "no", "not_sure"]},
            )
            add_case_timeline_event(report, "owner_handshake_sent", metadata={"sighting_id": sighting.id, "confidence_level": "medium"})
            return

    # No top match or below thresholds — just confirm receipt to sighter
    if sighting.sighter:
        _create_in_app(
            sighting.sighter,
            Notification.Type.SYSTEM,
            f"Your sighting in {sighting.sighting_city} has been received. Authorities will review it shortly.",
        )


def notify_owner_response(sighting, response, responder):
    """
    Handle owner responses: 'yes', 'no', 'not_sure'.
    - yes: escalate to authority (urgent), create owner response notification, mark for timeline
    - no: archive sighting, notify sighter + community
    - not_sure: mark status and wait for auto-escalation after deadline
    """
    now = timezone.now()
    report = _get_report_for_sighting(sighting)

    response = (response or "").lower()
    if response not in ("yes", "no", "not_sure"):
        raise ValueError("Invalid owner response")

    # Update sighting fields
    sighting.owner_confirmation_status = response
    sighting.owner_notified_at = now
    sighting.save(update_fields=["owner_confirmation_status", "owner_notified_at"])

    owner = responder

    if response == "yes":
        # Notify authorities with escalation flag
        for officer in _active_authorities_in(sighting.sighting_city or ""):
            _create_in_app(
                officer,
                Notification.Type.URGENT,
                f"Owner CONFIRMED sighting for {sighting.top_match_bike.make} {sighting.top_match_bike.model} in {sighting.sighting_city}. Act now.",
                report=report,
                sighting=sighting,
            )
        _create_in_app(owner, Notification.Type.SIGHTING_OWNER_RESPONSE, "Thanks — authorities have been escalated and will investigate.", report=report, sighting=sighting)
        add_case_timeline_event(report, "owner_confirmed_sighting", actor=owner, metadata={"sighting_id": sighting.id})
        return

    if response == "no":
        sighting.is_archived = True
        sighting.save(update_fields=["is_archived"])
        # Notify sighter that the sighting was archived
        if sighting.sighter:
            _create_in_app(
                sighting.sighter,
                Notification.Type.SYSTEM,
                "Your sighting was reviewed and archived (owner indicated it is not their bike). Thank you for reporting.",
                report=report,
                sighting=sighting,
            )
        # Optionally broadcast to reporter community — deferred for now
        _create_in_app(owner, Notification.Type.SIGHTING_OWNER_RESPONSE, "Thanks — record archived as per your response.", report=report, sighting=sighting)
        add_case_timeline_event(report, "owner_rejected_sighting", actor=owner, metadata={"sighting_id": sighting.id})
        return

    if response == "not_sure":
        # Leave pending — authorities will be auto-escalated after deadline via scheduled job
        _create_in_app(owner, Notification.Type.SIGHTING_OWNER_RESPONSE, "Thanks — we will follow up if needed. Authorities may be notified after a short timeout.", report=report, sighting=sighting)
        add_case_timeline_event(report, "owner_not_sure", actor=owner, metadata={"sighting_id": sighting.id})
        return


def auto_escalate_pending_owner_responses(hours=None):
    from apps.sightings.models import SightingReport

    now = timezone.now()
    grace_hours = hours if hours is not None else settings.SIGHTING_OWNER_RESPONSE_HOURS
    cutoff = now - timedelta(hours=grace_hours)
    pending = SightingReport.objects.filter(
        is_archived=False,
        auto_escalated=False,
        owner_response_deadline__isnull=False,
        owner_response_deadline__lt=now,
        owner_confirmation_status__in=["pending", "not_sure"],
    ).select_related("top_match_bike")

    escalated_count = 0
    for sighting in pending:
        report = _get_report_for_sighting(sighting)
        for officer in _active_authorities_in(sighting.sighting_city or ""):
            _create_in_app(
                officer,
                Notification.Type.URGENT,
                f"Owner did not confirm sighting #{sighting.id} in time. Auto-escalated for authority review.",
                report=report,
                sighting=sighting,
                metadata={"auto_escalated": True},
            )
        sighting.auto_escalated = True
        sighting.save(update_fields=["auto_escalated"])
        add_case_timeline_event(report, "owner_timeout_auto_escalation", metadata={"sighting_id": sighting.id, "deadline": str(sighting.owner_response_deadline), "cutoff": str(cutoff)})
        escalated_count += 1
    return escalated_count


def notify_case_closed_to_contributors(report):
    from apps.sightings.models import SightingReport

    sightings = SightingReport.objects.filter(
        top_match_bike=report.bike,
        is_archived=False,
        sighter__isnull=False,
    ).select_related("sighter")

    notified_users = set()
    for sighting in sightings:
        if sighting.sighter_id in notified_users:
            continue
        notified_users.add(sighting.sighter_id)
        _create_in_app(
            sighting.sighter,
            Notification.Type.COMMUNITY_CLOSURE,
            f"Case {report.reference_number} was resolved and the bike was recovered. Thanks to community reports like yours.",
            report=report,
            sighting=sighting,
        )
    add_case_timeline_event(report, "contributors_notified", metadata={"count": len(notified_users)})


def _get_report_for_sighting(sighting):
    from apps.reports.models import TheftReport

    bike = sighting.bike or sighting.top_match_bike
    if not bike:
        return None
    return (
        TheftReport.objects.filter(bike=bike, deleted_at__isnull=True)
        .exclude(status=TheftReport.Status.CLOSED)
        .order_by("-created_at")
        .first()
    )
