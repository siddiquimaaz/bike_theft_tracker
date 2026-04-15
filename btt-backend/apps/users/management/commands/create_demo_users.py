"""
Management command: create_demo_users
Creates demo accounts used by the login page and Playwright E2E tests.

Usage:
    python manage.py create_demo_users          # create if not exist
    python manage.py create_demo_users --reset  # delete first, then recreate
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

DEMO_USERS = [
    {
        "email":        "admin@demo.btt",
        "password":     "DemoAdmin@2024",
        "full_name":    "Demo Admin",
        "role":         "admin",
        "city":         "Karachi",
        "is_verified":  True,
        "is_active":    True,
        "is_staff":     True,
        "is_superuser": True,
    },
    {
        "email":        "authority.karachi@demo.btt",
        "password":     "Authority@2024",
        "full_name":    "Inspector Ali Khan",
        "role":         "authority",
        "city":         "Karachi",
        "badge_number": "KHI-0001",
        "cnic":         "4210100000001",
        "is_verified":  True,
        "is_active":    True,
    },
    {
        "email":       "owner000@demo.btt",
        "password":    "Owner@2024",
        "full_name":   "Demo Owner",
        "role":        "owner",
        "city":        "Karachi",
        "cnic":        "4210100000002",
        "is_verified": True,
        "is_active":   True,
    },
    {
        "email":       "community@demo.btt",
        "password":    "Community@2024",
        "full_name":   "Community Reporter",
        "role":        "community",
        "city":        "Lahore",
        "is_verified": True,
        "is_active":   True,
    },
]


class Command(BaseCommand):
    help = "Seed demo user accounts for development and E2E testing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing demo accounts before recreating them.",
        )

    def handle(self, *args, **options):
        emails = [u["email"] for u in DEMO_USERS]

        if options["reset"]:
            deleted, _ = User.objects.filter(email__in=emails).delete()
            self.stdout.write(self.style.WARNING(f"Deleted {deleted} existing demo user(s)."))

        created = 0
        for spec in DEMO_USERS:
            # Work on a copy so DEMO_USERS is never mutated
            data     = dict(spec)
            password = data.pop("password")

            if User.objects.filter(email=data["email"]).exists():
                self.stdout.write(f"  Exists   [{data['role']:10s}]  {data['email']}")
                continue

            # Use create_user so password is properly hashed
            user = User.objects.create_user(
                email    = data.pop("email"),
                password = password,
                **data,
            )
            created += 1
            self.stdout.write(self.style.SUCCESS(
                f"  Created  [{user.role:10s}]  {user.email}"
            ))

        self.stdout.write(self.style.SUCCESS(
            f"\nDone — {created} new demo user(s) created."
        ))
        self.stdout.write("\nDemo credentials:")
        for u in DEMO_USERS:
            self.stdout.write(f"  {u['role']:10s}  {u['email']}  /  {u['password']}")
