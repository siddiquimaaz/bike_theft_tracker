"""
apps/reports/models.py
TheftReport — the central entity. Status is a state machine that drives
the entire application workflow.
RecoveryRecord — one-to-one with TheftReport, created when bike is found.
"""
from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.db import models
from django.utils import timezone


class TheftReport(models.Model):
    class Status(models.TextChoices):
        STOLEN = "stolen", "Stolen (Legacy)"
        UNDER_INVESTIGATION = "under_investigation", "Under Investigation (Legacy)"
        NEW_CASE = "new_case", "New Case"
        UNDER_REVIEW = "under_review", "Under Review"
        ACTIVE_INVESTIGATION = "active_investigation", "Active Investigation"
        BIKE_LOCATED = "bike_located", "Bike Located"
        PENDING_VERIFICATION = "pending_verification", "Pending Verification"
        RECOVERED = "recovered", "Recovered"
        CLOSED = "closed", "Closed"

    # Core references
    bike = models.ForeignKey(
        "bikes.Bike",
        on_delete=models.PROTECT,
        related_name="theft_reports",
    )
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="filed_reports",
        limit_choices_to={"role": "owner"},
    )

    # Theft details
    theft_date = models.DateField(help_text="Date the theft occurred — not necessarily today")
    theft_city = models.CharField(max_length=80)
    theft_location = gis_models.PointField(
        srid=4326, null=True, blank=True,
        help_text="PostGIS POINT (longitude, latitude) from map pin — WGS84"
    )
    theft_location_detail = models.TextField(
        null=True, blank=True,
        help_text="Free-text: street name, landmark, area"
    )
    fir_number = models.CharField(
        max_length=50, null=True, blank=True,
        help_text="Police FIR number if filed at station"
    )
    description = models.TextField(null=True, blank=True,
                                   help_text="Owner narrative of theft circumstances")

    # State machine — drives entire app behavior
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.NEW_CASE,
    )
    owner_recovery_confirmed = models.BooleanField(
        default=False,
        help_text="Owner must confirm pickup/receipt before final case closure.",
    )
    owner_recovery_confirmed_at = models.DateTimeField(null=True, blank=True)
    owner_recovery_confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="confirmed_recoveries",
        limit_choices_to={"role": "owner"},
    )
    authority_last_action_at = models.DateTimeField(
        default=timezone.now,
        help_text="Used for stale-case automation and reminders.",
    )
    stale_escalated_at = models.DateTimeField(null=True, blank=True)

    # Timestamps & soft delete
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Soft delete — evidence records are never hard-deleted"
    )

    class Meta:
        db_table = "theft_reports"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Report #{self.id} — {self.bike} [{self.status}]"

    @property
    def reference_number(self):
        return f"BTT-{self.id:04d}"

    def transition_status(self, new_status: str, changed_by):
        """
        Enforce valid state transitions:
        new_case -> under_review -> active_investigation -> bike_located
        -> pending_verification -> recovered -> closed
        """
        valid_transitions = {
            self.Status.STOLEN: [self.Status.UNDER_INVESTIGATION, self.Status.CLOSED],
            self.Status.UNDER_INVESTIGATION: [self.Status.RECOVERED, self.Status.CLOSED],
            self.Status.NEW_CASE: [
                self.Status.UNDER_REVIEW,
                self.Status.UNDER_INVESTIGATION,  # Legacy client compatibility
                self.Status.CLOSED,
            ],
            self.Status.UNDER_REVIEW: [self.Status.ACTIVE_INVESTIGATION, self.Status.CLOSED],
            self.Status.ACTIVE_INVESTIGATION: [self.Status.BIKE_LOCATED, self.Status.CLOSED],
            self.Status.BIKE_LOCATED: [self.Status.PENDING_VERIFICATION, self.Status.CLOSED],
            self.Status.PENDING_VERIFICATION: [self.Status.RECOVERED, self.Status.CLOSED],
            self.Status.RECOVERED: [self.Status.CLOSED],
            self.Status.CLOSED: [],
        }
        if new_status not in valid_transitions.get(self.status, []):
            raise ValueError(
                f"Cannot transition from '{self.status}' to '{new_status}'. "
                f"Valid next states: {valid_transitions.get(self.status, [])}"
            )
        old_status = self.status
        self.status = new_status
        self.authority_last_action_at = timezone.now()
        self.save(update_fields=["status", "updated_at", "authority_last_action_at"])
        return old_status


class RecoveryRecord(models.Model):
    class BikeCondition(models.TextChoices):
        GOOD = "good", "Good"
        DAMAGED = "damaged", "Damaged"
        STRIPPED = "stripped", "Stripped"
        BURNT = "burnt", "Burnt"

    # One recovery per report — enforced by UNIQUE constraint
    theft_report = models.OneToOneField(
        TheftReport,
        on_delete=models.PROTECT,
        related_name="recovery",
    )
    logged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="logged_recoveries",
        limit_choices_to={"role": "authority"},
    )

    # Fuzzy match context
    fuzzy_match_score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="rapidfuzz WRatio confidence score used to identify this bike (0-100)"
    )

    # Recovery details
    recovery_date = models.DateField()
    recovery_city = models.CharField(max_length=80)
    recovery_location = gis_models.PointField(
        srid=4326, null=True, blank=True,
        help_text="PostGIS POINT — used in recovery zone spatial analysis"
    )
    recovery_location_detail = models.TextField(null=True, blank=True)
    bike_condition = models.CharField(
        max_length=20,
        choices=BikeCondition.choices,
        null=True, blank=True,
    )
    notes = models.TextField(null=True, blank=True)

    # Evidence photos — stored as JSON array of UUID filenames
    evidence_photos = models.JSONField(
        null=True, blank=True,
        default=list,
        help_text="Array of UUID filenames: ['uuid1.jpg', 'uuid2.jpg']. Max 5 files, 2MB each."
    )

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "recovery_records"

    def __str__(self):
        return f"Recovery for Report #{self.theft_report_id} — {self.recovery_date}"


class CaseTimeline(models.Model):
    theft_report = models.ForeignKey(
        TheftReport,
        on_delete=models.CASCADE,
        related_name="timeline",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    action = models.CharField(max_length=100)
    metadata = models.JSONField(default=dict, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "case_timeline"
        ordering = ["created_at"]

    def __str__(self):
        return f"Timeline: {self.theft_report_id} — {self.action} @ {self.created_at}"
