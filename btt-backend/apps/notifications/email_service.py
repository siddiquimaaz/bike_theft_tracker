"""
apps/notifications/email_service.py
All transactional email functions.
Each function is called from a daemon thread — failures are logged but
NEVER raise exceptions that could affect the API response.
"""
import logging
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def _safe_send(subject: str, body: str, recipient: str):
    """Send a plain-text email. Logs and swallows exceptions."""
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
        logger.info("Email sent: '%s' → %s", subject, recipient)
    except Exception as exc:
        logger.error("Email delivery failed to %s: %s", recipient, exc, exc_info=True)


def send_email_verification(user):
    """Registration verification link — expires in 24 hours."""
    link = f"{settings.FRONTEND_URL}/verify-email/{user.email_verification_token}"
    _safe_send(
        subject="[Bike Theft Tracker] Verify Your Email",
        body=(
            f"Hello {user.full_name},\n\n"
            f"Please verify your email address by clicking the link below.\n"
            f"This link expires in 24 hours.\n\n"
            f"{link}\n\n"
            f"If you did not register, please ignore this email.\n\n"
            f"— Bike Theft Tracker Team"
        ),
        recipient=user.email,
    )


def send_password_reset_email(user):
    """Password reset link — expires in 1 hour, single-use."""
    link = f"{settings.FRONTEND_URL}/reset-password/{user.password_reset_token}"
    _safe_send(
        subject="[Bike Theft Tracker] Password Reset Request",
        body=(
            f"Hello {user.full_name},\n\n"
            f"A password reset was requested for your account.\n"
            f"Click the link below to set a new password. This link expires in 1 hour.\n\n"
            f"{link}\n\n"
            f"If you did not request this, please ignore this email.\n\n"
            f"— Bike Theft Tracker Team"
        ),
        recipient=user.email,
    )


def send_authority_credentials_email(user):
    """Welcome email to a newly created authority officer account."""
    _safe_send(
        subject="[Bike Theft Tracker] Your Authority Account Has Been Created",
        body=(
            f"Hello {user.full_name},\n\n"
            f"A Police Authority account has been created for you on Bike Theft Tracker.\n\n"
            f"Login Email: {user.email}\n"
            f"Badge Number: {user.badge_number}\n"
            f"Assigned City: {user.city or 'Not set'}\n\n"
            f"Please contact your administrator for your initial password.\n\n"
            f"Login at: {settings.FRONTEND_URL}/login\n\n"
            f"— Bike Theft Tracker Team"
        ),
        recipient=user.email,
    )


def send_theft_reported_email(user, report):
    """Confirmation email to owner after theft report is filed."""
    _safe_send(
        subject=f"[Bike Theft Tracker] Theft Report Confirmed — {report.reference_number}",
        body=(
            f"Hello {user.full_name},\n\n"
            f"Your theft report has been received and is now active.\n\n"
            f"Reference Number: {report.reference_number}\n"
            f"Bike: {report.bike.year} {report.bike.make} {report.bike.model}\n"
            f"Theft Date: {report.theft_date}\n"
            f"City: {report.theft_city}\n"
            f"Status: {report.status}\n\n"
            f"Keep your reference number for all future inquiries.\n\n"
            f"— Bike Theft Tracker Team"
        ),
        recipient=user.email,
    )


def send_status_update_email(user, report, old_status):
    """Notifies owner when case status changes."""
    _safe_send(
        subject=f"[Bike Theft Tracker] Case Update — {report.reference_number}",
        body=(
            f"Hello {user.full_name},\n\n"
            f"Your case {report.reference_number} has been updated.\n\n"
            f"Previous Status: {old_status}\n"
            f"New Status: {report.status}\n"
            f"Bike: {report.bike.year} {report.bike.make} {report.bike.model}\n\n"
            f"Log in to view full case details.\n\n"
            f"— Bike Theft Tracker Team"
        ),
        recipient=user.email,
    )


def send_recovery_email(user, report, recovery):
    """URGENT recovery notification to bike owner — email + SMS triggered here."""
    officer = recovery.logged_by
    _safe_send(
        subject=f"[Bike Theft Tracker] YOUR BIKE HAS BEEN RECOVERED — {report.reference_number}",
        body=(
            f"Hello {user.full_name},\n\n"
            f"GREAT NEWS — your {report.bike.year} {report.bike.make} {report.bike.model} "
            f"(Engine: {report.bike.engine_number}) has been recovered!\n\n"
            f"Recovery Date: {recovery.recovery_date}\n"
            f"Recovery City: {recovery.recovery_city}\n"
            f"Recovery Location: {recovery.recovery_location_detail or 'See case details'}\n"
            f"Bike Condition: {recovery.bike_condition or 'Not specified'}\n"
            f"Recovery Officer: {officer.full_name}\n"
            f"Officer Contact: {officer.phone or 'Contact your local station'}\n\n"
            f"Please visit your local police station with your ownership documents "
            f"to claim your vehicle.\n\n"
            f"— Bike Theft Tracker Team"
        ),
        recipient=user.email,
    )


def send_sighting_verified_email(user, sighting):
    """Notifies owner when a community sighting of their bike is verified by authority."""
    _safe_send(
        subject=f"[Bike Theft Tracker] URGENT: Verified Sighting of Your Bike",
        body=(
            f"Hello {user.full_name},\n\n"
            f"A verified sighting of your {sighting.bike.year} {sighting.bike.make} "
            f"{sighting.bike.model} has been reported.\n\n"
            f"Sighting Date: {sighting.sighting_date}\n"
            f"Sighting City: {sighting.sighting_city}\n"
            f"Description: {sighting.sighting_description or 'None provided'}\n"
            f"Verified by: {sighting.verified_by.full_name if sighting.verified_by else 'Authority'}\n\n"
            f"Authorities have been notified. Please do not attempt recovery yourself.\n\n"
            f"— Bike Theft Tracker Team"
        ),
        recipient=user.email,
    )


def send_recovery_amended_email(user, report, recovery, officer):
    """Notifies owner when a recovery record is updated by officer."""
    _safe_send(
        subject=f"[Bike Theft Tracker] Recovery Details Updated — {report.reference_number}",
        body=(
            f"Hello {user.full_name},\n\n"
            f"The recovery details for your case {report.reference_number} have been updated "
            f"by {officer.full_name}.\n\n"
            f"Updated Condition: {recovery.bike_condition or 'Not specified'}\n"
            f"Updated Location: {recovery.recovery_location_detail or 'See case details'}\n\n"
            f"Please log in to review the updated recovery record.\n\n"
            f"— Bike Theft Tracker Team"
        ),
        recipient=user.email,
    )
