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

    from .email_service import send_theft_reported_email
    send_theft_reported_email(owner, report)


# ─── Trigger: Status Changed ──────────────────────────────────────────────────

def notify_status_changed(report, old_status):
    owner = report.reported_by
    message = (
        f"Case {report.reference_number} status changed: "
        f"{old_status} → {report.status}."
    )
    _create_in_app(owner, Notification.Type.STATUS_UPDATE, message, report)

    from .email_service import send_status_update_email
    send_status_update_email(owner, report, old_status)


# ─── Trigger: Bike Recovered ──────────────────────────────────────────────────

def notify_bike_recovered(report, recovery):
    owner = report.reported_by
    message = (
        f"Your {report.bike.make} {report.bike.model} has been RECOVERED "
        f"in {recovery.recovery_city} on {recovery.recovery_date}. "
        f"Condition: {recovery.bike_condition or 'not specified'}."
    )
    _create_in_app(owner, Notification.Type.RECOVERY, message, report)

    from .email_service import send_recovery_email
    send_recovery_email(owner, report, recovery)

    from .sms_service import send_recovery_sms
    send_recovery_sms(owner, report, recovery)


# ─── Trigger: Recovery Record Amended ─────────────────────────────────────────

def notify_recovery_amended(report, recovery, officer):
    owner = report.reported_by
    message = (
        f"Recovery details for case {report.reference_number} were updated "
        f"by {officer.full_name}. New condition: {recovery.bike_condition or 'not specified'}."
    )
    _create_in_app(owner, Notification.Type.STATUS_UPDATE, message, report)

    from .email_service import send_recovery_amended_email
    send_recovery_amended_email(owner, report, recovery, officer)


# ─── Trigger: Sighting Submitted ──────────────────────────────────────────────

def notify_sighting_submitted(sighting):
    """Notifies the sighter that their report was received."""
    if not sighting.sighter:
        return
    message = (
        f"Thank you for your sighting report in {sighting.sighting_city}. "
        f"Status: Pending Verification."
    )
    _create_in_app(sighting.sighter, Notification.Type.SYSTEM, message)


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

    # Email + SMS for high-priority sighting
    from .email_service import send_sighting_verified_email
    send_sighting_verified_email(owner, sighting)

    from .sms_service import send_sighting_verified_sms
    send_sighting_verified_sms(owner, sighting)
