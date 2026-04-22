"""
Notification domain workflows and routing logic.
"""
import logging
from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from apps.reports.timeline import add_case_timeline_event
from .models import Notification

logger = logging.getLogger(__name__)


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
    owner = report.reported_by
    message = (
        f"Your theft report has been filed. "
        f"Reference: {report.reference_number}. "
        f"Bike: {report.bike.make} {report.bike.model}."
    )
    _create_in_app(owner, Notification.Type.THEFT_REPORTED, message, report)
    add_case_timeline_event(report, "report_filed", actor=owner, metadata={"status": report.status})

    # TODO (future release): send_theft_reported_email(owner, report)
    # Requires EMAIL_HOST_USER + EMAIL_HOST_PASSWORD in .env


# ─── Trigger: Status Changed ──────────────────────────────────────────────────

def notify_status_changed(report, old_status):
    owner = report.reported_by
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


# ─── Trigger: Sighting Submitted ──────────────────────────────────────────────

# Minimum fuzzy-match score that triggers an owner alert on submission.
# Below this threshold the match is too uncertain to notify.
_OWNER_ALERT_THRESHOLD = 70

def notify_sighting_submitted(sighting):
    """
    1. Confirms receipt to the sighter (in-app).
    2. If the fuzzy match score meets the threshold and a top-match bike
       exists, alerts the bike owner immediately (in-app) — they don't
       have to wait for authority verification to learn about the sighting.
    """
    # ── Notify the sighter ───────────────────────────────────────────────
    if sighting.sighter:
        score_note = (
            f" A potential match was found ({sighting.fuzzy_match_score:.0f}% confidence)."
            if sighting.fuzzy_match_score and sighting.fuzzy_match_score >= _OWNER_ALERT_THRESHOLD
            else ""
        )
        _create_in_app(
            sighting.sighter,
            Notification.Type.SYSTEM,
            f"Your sighting in {sighting.sighting_city} has been received."
            f"{score_note} Authorities will review it shortly.",
        )

    # ── Alert the bike owner if confidence is high enough ────────────────
    if (
        sighting.fuzzy_match_score is not None
        and sighting.fuzzy_match_score >= _OWNER_ALERT_THRESHOLD
        and sighting.top_match_bike is not None
    ):
        owner = sighting.top_match_bike.owner
        bike = sighting.top_match_bike
        _create_in_app(
            owner,
            Notification.Type.SIGHTING_MATCHED,
            f"A community sighting in {sighting.sighting_city} on {sighting.sighting_date} "
            f"may match your {bike.make} {bike.model} "
            f"({sighting.fuzzy_match_score:.0f}% confidence). "
            f"Authorities have been notified and are reviewing the report.",
        )

        # Notify authority users in the same city and all admins so the
        # verification queue is acted on quickly.
        from apps.users.models import User
        authority_qs = User.objects.filter(
            role=User.Role.AUTHORITY,
            is_active=True,
            city__iexact=sighting.sighting_city or "",
        )
        admin_qs = User.objects.filter(role=User.Role.ADMIN, is_active=True)
        for officer in authority_qs:
            _create_in_app(
                officer,
                Notification.Type.SYSTEM,
                f"New high-confidence sighting submitted in {sighting.sighting_city} "
                f"({sighting.fuzzy_match_score:.0f}%). Review and verify promptly.",
            )
        for admin in admin_qs:
            _create_in_app(
                admin,
                Notification.Type.SYSTEM,
                f"High-confidence sighting submitted in {sighting.sighting_city}; "
                f"authority review pending.",
            )


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
    OWNER_ALERT_THRESHOLD = getattr(settings, "OWNER_ALERT_THRESHOLD", 70)
    PHOTO_HIGH_CONFIDENCE_THRESHOLD = getattr(settings, "PHOTO_HIGH_CONFIDENCE_THRESHOLD", 85)
    OWNER_RESPONSE_HOURS = getattr(settings, "SIGHTING_OWNER_RESPONSE_HOURS", 24)
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
        if has_photo and score >= PHOTO_HIGH_CONFIDENCE_THRESHOLD:
            sighting.owner_confirmation_status = "pending"
            sighting.owner_notified_at = now
            sighting.owner_response_deadline = now + timedelta(hours=OWNER_RESPONSE_HOURS)
            sighting.save(update_fields=["owner_confirmation_status", "owner_notified_at", "owner_response_deadline"])

            _create_in_app(
                owner,
                Notification.Type.SIGHTING_OWNER_HANDSHAKE,
                f"Is this your {sighting.top_match_bike.make} {sighting.top_match_bike.model} (Reported {sighting.sighting_date})? Reply Yes / No / Not Sure.",
                report=report,
                sighting=sighting,
                metadata={"requires_response": True, "response_options": ["yes", "no", "not_sure"]},
            )

            # Notify authorities urgently
            from apps.users.models import User
            authority_qs = User.objects.filter(
                role=User.Role.AUTHORITY,
                is_active=True,
                city__iexact=sighting.sighting_city or "",
            )
            for officer in authority_qs:
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
        if score >= OWNER_ALERT_THRESHOLD:
            sighting.owner_confirmation_status = "pending"
            sighting.owner_notified_at = now
            sighting.owner_response_deadline = now + timedelta(hours=OWNER_RESPONSE_HOURS)
            sighting.save(update_fields=["owner_confirmation_status", "owner_notified_at", "owner_response_deadline"])

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
        from apps.users.models import User
        authority_qs = User.objects.filter(
            role=User.Role.AUTHORITY,
            is_active=True,
            city__iexact=sighting.sighting_city or "",
        )
        for officer in authority_qs:
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
    from apps.users.models import User

    now = timezone.now()
    grace_hours = hours if hours is not None else getattr(settings, "SIGHTING_OWNER_RESPONSE_HOURS", 24)
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
        authority_qs = User.objects.filter(
            role=User.Role.AUTHORITY,
            is_active=True,
            city__iexact=sighting.sighting_city or "",
        )
        for officer in authority_qs:
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
