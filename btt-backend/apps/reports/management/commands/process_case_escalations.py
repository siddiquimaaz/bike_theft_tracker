from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.notifications.models import Notification
from apps.reports.models import TheftReport
from apps.reports.timeline import add_case_timeline_event
from apps.users.models import User


class Command(BaseCommand):
    help = "Send authority reminders for stale cases and escalate prolonged inactivity."

    def handle(self, *args, **options):
        now = timezone.now()
        reminder_cutoff = now - timedelta(hours=48)
        stale_cutoff = now - timedelta(days=7)

        reminded = 0
        stale_flagged = 0

        reminders = TheftReport.objects.filter(
            deleted_at__isnull=True,
            status__in=[
                TheftReport.Status.UNDER_REVIEW,
                TheftReport.Status.ACTIVE_INVESTIGATION,
                TheftReport.Status.BIKE_LOCATED,
                TheftReport.Status.PENDING_VERIFICATION,
            ],
            authority_last_action_at__lt=reminder_cutoff,
        )
        for report in reminders:
            authorities = User.objects.filter(
                role=User.Role.AUTHORITY,
                is_active=True,
                city__iexact=report.theft_city,
            )
            for officer in authorities:
                Notification.objects.create(
                    user=officer,
                    report=report,
                    type=Notification.Type.SYSTEM,
                    message=f"Reminder: Case {report.reference_number} has no authority update in 48 hours.",
                    delivery_channel=Notification.Channel.IN_APP,
                )
            add_case_timeline_event(report, "authority_reminder_sent", metadata={"hours_without_update": 48})
            reminded += 1

        stale_reports = reminders.filter(
            authority_last_action_at__lt=stale_cutoff,
            stale_escalated_at__isnull=True,
        )
        for report in stale_reports:
            senior_admins = User.objects.filter(role=User.Role.ADMIN, is_active=True)
            for admin in senior_admins:
                Notification.objects.create(
                    user=admin,
                    report=report,
                    type=Notification.Type.URGENT,
                    message=f"Stale case escalation: {report.reference_number} has no updates for 7 days.",
                    delivery_channel=Notification.Channel.IN_APP,
                )
            report.stale_escalated_at = now
            report.save(update_fields=["stale_escalated_at"])
            add_case_timeline_event(report, "case_stale_escalated", metadata={"days_without_update": 7})
            stale_flagged += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Sent reminders for {reminded} cases and stale-escalated {stale_flagged} cases."
            )
        )
