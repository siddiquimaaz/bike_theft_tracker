"""
apps/sightings/models.py
Community-submitted bike sightings. All sightings are unverified by default.
Authority officers verify before acting. Fuzzy match runs automatically on submission.
"""
from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.db import models
from django.utils import timezone


class SightingReport(models.Model):
    # Linked bike — NULL until authority verifies and matches the sighting
    bike = models.ForeignKey(
        "bikes.Bike",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="sightings",
        help_text="FK → bikes — NULL until authority verifies"
    )

    # What the reporter entered — may be partial or have typos
    raw_engine_number = models.CharField(
        max_length=50, null=True, blank=True,
        help_text="What community reporter entered — may be partial or incorrect"
    )
    raw_chassis_number = models.CharField(max_length=50, null=True, blank=True)

    # Fuzzy match result computed at submission time
    fuzzy_match_score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Best rapidfuzz score at submission time"
    )
    top_match_bike = models.ForeignKey(
        "bikes.Bike",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="top_match_sightings",
        help_text="Best fuzzy match candidate — shown to authority for review"
    )

    # Who submitted
    sighter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="sightings",
    )

    # Sighting location details
    sighting_date = models.DateField()
    sighting_city = models.CharField(max_length=80)
    sighting_location = gis_models.PointField(srid=4326, null=True, blank=True)
    sighting_description = models.TextField(null=True, blank=True)
    photo_url = models.CharField(
        max_length=255, null=True, blank=True,
        help_text="UUID filename of sighting photo stored in /media/sightings/"
    )

    # Verification
    is_verified = models.BooleanField(
        default=False,
        help_text="FALSE = unverified community report. TRUE = authority confirmed."
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="verified_sightings",
        limit_choices_to={"role": "authority"},
    )

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "sighting_reports"
        ordering = ["-fuzzy_match_score", "-created_at"]

    def __str__(self):
        return (
            f"Sighting #{self.id} in {self.sighting_city} — "
            f"{'Verified' if self.is_verified else 'Unverified'}"
        )
