"""
apps/notifications/models.py
All system notifications — in-app, email, SMS.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


class Notification(models.Model):
    class Type(models.TextChoices):
        THEFT_REPORTED = "theft_reported", "Theft Reported"
        STATUS_UPDATE = "status_update", "Status Update"
        RECOVERY = "recovery", "Vehicle Recovered"
        SIGHTING_MATCHED = "sighting_matched", "Sighting Matched"
        SYSTEM = "system", "System Notification"

    class Channel(models.TextChoices):
        EMAIL = "email", "Email"
        SMS = "sms", "SMS"
        IN_APP = "in_app", "In-App"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    report = models.ForeignKey(
        "reports.TheftReport",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="notifications",
        help_text="Context report — NULL for system notifications"
    )

    type = models.CharField(max_length=30, choices=Type.choices)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    delivery_channel = models.CharField(max_length=20, choices=Channel.choices)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.type}] → {self.user.email} ({'read' if self.is_read else 'unread'})"
