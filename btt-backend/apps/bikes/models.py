"""
apps/bikes/models.py
Registered motorcycles linked to owners.
Engine and chassis numbers are the TRUE unique identifiers — immutable after registration.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


class Bike(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="bikes",
        limit_choices_to={"role": "owner"},
    )

    # Identity — must match registration documents
    make = models.CharField(max_length=60,
                            help_text="Manufacturer: Honda, Yamaha, Suzuki, United, Road Prince")
    model = models.CharField(max_length=60,
                             help_text="Model name: CD 70, CG 125, YBR 125")
    year = models.SmallIntegerField(help_text="Manufacturing year (4 digits)")
    color = models.CharField(max_length=40, null=True, blank=True)
    registration_number = models.CharField(
        max_length=20, null=True, blank=True,
        help_text="License plate — may change; not used as unique ID"
    )
    registration_city = models.CharField(max_length=80, null=True, blank=True)

    # Immutable identifiers — targets of fuzzy matching
    engine_number = models.CharField(
        max_length=50, unique=True,
        help_text="TRUE unique identifier — cannot legally be changed. Target of fuzzy matching."
    )
    chassis_number = models.CharField(
        max_length=50, unique=True,
        help_text="Secondary unique identifier stamped on frame"
    )

    # Optional photo
    photo_url = models.CharField(
        max_length=255, null=True, blank=True,
        help_text="UUID filename stored in /media/bikes/"
    )

    created_at = models.DateTimeField(default=timezone.now)
    deleted_at = models.DateTimeField(null=True, blank=True,
                                      help_text="Soft delete — cannot delete if active theft report")

    class Meta:
        db_table = "bikes"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.year} {self.make} {self.model} — {self.engine_number}"

    @property
    def is_stolen(self):
        from apps.reports.models import TheftReport

        return self.theft_reports.filter(
            status__in=TheftReport.ACTIVE_STATUSES,
            deleted_at__isnull=True,
        ).exists()

    @property
    def active_theft_report(self):
        from apps.reports.models import TheftReport

        return self.theft_reports.filter(
            status__in=TheftReport.ACTIVE_STATUSES,
            deleted_at__isnull=True,
        ).first()

    def soft_delete(self):
        if self.is_stolen:
            raise ValueError("Cannot delete a bike with an active theft report.")
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])
