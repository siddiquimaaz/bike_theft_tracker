from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.notifications.notification_service import auto_escalate_pending_owner_responses
from apps.notifications.models import Notification
from apps.sightings.models import SightingReport


class Command(BaseCommand):
    help = "Auto-escalate sighting handshakes that exceeded owner response deadline."

    def handle(self, *args, **options):
        now = timezone.now()
        nudges_sent = 0
        for sighting in SightingReport.objects.filter(
            is_archived=False,
            auto_escalated=False,
            owner_confirmation_status="pending",
            owner_response_deadline__isnull=False,
        ).select_related("top_match_bike"):
            if not sighting.top_match_bike:
                continue
            remaining = sighting.owner_response_deadline - now
            if remaining.total_seconds() > 24 * 3600:
                continue
            owner = sighting.top_match_bike.owner
            already_nudged = Notification.objects.filter(
                user=owner,
                sighting=sighting,
                type=Notification.Type.SYSTEM,
                message__icontains="Reminder: please confirm",
            ).exists()
            if already_nudged:
                continue
            Notification.objects.create(
                user=owner,
                sighting=sighting,
                type=Notification.Type.SYSTEM,
                message="Reminder: please confirm if the reported sighting is your bike.",
                delivery_channel=Notification.Channel.IN_APP,
            )
            nudges_sent += 1

        escalated = auto_escalate_pending_owner_responses()
        self.stdout.write(
            self.style.SUCCESS(
                f"Sent {nudges_sent} owner nudges and auto-escalated {escalated} pending sighting handshakes."
            )
        )
