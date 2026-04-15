"""
apps/notifications/sms_service.py
Twilio SMS — sent only for high-priority events:
  - Verified sighting of stolen bike
  - Vehicle recovered
"""
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def _safe_sms(body: str, to_number: str):
    """Send SMS via Twilio. Non-blocking — logs and swallows exceptions."""
    if not all([settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN, settings.TWILIO_FROM_NUMBER]):
        logger.warning("Twilio credentials not configured — SMS not sent to %s", to_number)
        return
    if not to_number:
        logger.warning("No phone number — SMS skipped")
        return
    try:
        from twilio.rest import Client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=body,
            from_=settings.TWILIO_FROM_NUMBER,
            to=to_number,
        )
        logger.info("SMS sent SID=%s → %s", message.sid, to_number)
    except Exception as exc:
        logger.error("SMS delivery failed to %s: %s", to_number, exc, exc_info=True)


def send_recovery_sms(user, report, recovery):
    """URGENT SMS — bike recovered."""
    if not user.phone:
        return
    body = (
        f"BTT ALERT: Your {report.bike.make} {report.bike.model} "
        f"(Engine: {report.bike.engine_number[:8]}...) has been RECOVERED "
        f"in {recovery.recovery_city} on {recovery.recovery_date}. "
        f"Condition: {recovery.bike_condition or 'unknown'}. "
        f"Visit your local station with ownership docs. Ref: {report.reference_number}"
    )
    _safe_sms(body, user.phone)


def send_sighting_verified_sms(user, sighting):
    """URGENT SMS — verified sighting of stolen bike."""
    if not user.phone:
        return
    body = (
        f"BTT URGENT: A verified sighting of your "
        f"{sighting.bike.make} {sighting.bike.model} was reported "
        f"in {sighting.sighting_city} on {sighting.sighting_date}. "
        f"Authorities notified. Do NOT attempt recovery yourself."
    )
    _safe_sms(body, user.phone)
