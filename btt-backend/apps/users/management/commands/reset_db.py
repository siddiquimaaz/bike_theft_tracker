from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.conf import settings
import os


class Command(BaseCommand):
    help = "Safely flush all data from the Django database. Use with caution."

    def add_arguments(self, parser):
        parser.add_argument(
            "--noinput",
            action="store_true",
            help="Don't prompt for confirmation (use with --force).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force reset even if DEBUG is False. Use with care.",
        )

    def handle(self, *args, **options):
        force = options.get("force")
        noinput = options.get("noinput")

        # Safety: refuse unless DEBUG or --force provided
        if not settings.DEBUG and not force:
            raise CommandError(
                "Refusing to reset DB because DEBUG is False. Re-run with --force to override."
            )

        if not noinput and not force:
            confirm = input(
                "This will flush ALL data from the database (tables remain). Type 'YES' to continue: "
            )
            if confirm != "YES":
                self.stdout.write(self.style.WARNING("Aborted by user."))
                return

        self.stdout.write(self.style.WARNING("Running: python manage.py flush --noinput"))
        try:
            # Call Django's flush which truncates data and resets sequences
            call_command("flush", "--noinput")
        except Exception as exc:
            raise CommandError(f"Failed to flush DB: {exc}")

        self.stdout.write(self.style.SUCCESS("Database flush complete."))
