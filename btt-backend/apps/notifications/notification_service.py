"""
apps/notifications/notification_service.py
Central dispatcher for all notification events.
Creates in-app Notification records AND triggers email/SMS.
All external calls are non-blocking — run in daemon threads at call site.
"""
import logging
from .models import Notification

logger = logging.getLogger(__name__)


def _create_in_app(user, notification_type, message, report=None):
    """Persist an in-app notification."""
    try:
        Notification.objects.create(
            user=user,
            report=report,
            type=notification_type,
            message=message,
            delivery_channel=Notification.Channel.IN_APP,
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

    # TODO (future release): send_status_update_email(owner, report, old_status)


# ─── Trigger: Bike Recovered ──────────────────────────────────────────────────

def notify_bike_recovered(report, recovery):
    owner = report.reported_by
    message = (
        f"Your {report.bike.make} {report.bike.model} has been RECOVERED "
        f"in {recovery.recovery_city} on {recovery.recovery_date}. "
        f"Condition: {recovery.bike_condition or 'not specified'}."
    )
    _create_in_app(owner, Notification.Type.RECOVERY, message, report)

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
    _create_in_app(owner, Notification.Type.SIGHTING_MATCHED, message)

    # TODO (future release): send_sighting_verified_email(owner, sighting)
    # TODO (future release): send_sighting_verified_sms(owner, sighting)
