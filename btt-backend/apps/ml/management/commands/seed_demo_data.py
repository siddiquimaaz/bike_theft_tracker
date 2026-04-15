"""
apps/ml/management/commands/seed_demo_data.py

Seeds the database with 100+ realistic Pakistani motorcycle theft records
across multiple cities. Required before ML models can demonstrate results.

Usage:
    python manage.py seed_demo_data
    python manage.py seed_demo_data --clear   # wipe existing demo data first
"""
import random
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point


# Pakistan city coordinates (lat, lng) + name
CITIES = [
    ("Karachi",   24.8607,  67.0011),
    ("Lahore",    31.5204,  74.3587),
    ("Islamabad", 33.6844,  73.0479),
    ("Rawalpindi",33.6007,  73.0679),
    ("Faisalabad",31.4504,  73.1350),
    ("Peshawar",  34.0151,  71.5249),
    ("Quetta",    30.1798,  66.9750),
    ("Multan",    30.1575,  71.5249),
]

MAKES = ["Honda", "Yamaha", "Suzuki", "United", "Road Prince", "Ravi", "Super Star"]
MODELS = {
    "Honda":       ["CD 70", "CG 125", "CB 125F", "Pridor 100"],
    "Yamaha":      ["YBR 125", "YBR 125G", "YB 125Z"],
    "Suzuki":      ["GD 110", "GR 150", "Mehran"],
    "United":      ["US 70", "US 100"],
    "Road Prince": ["RP 70", "RP 110"],
    "Ravi":        ["Piaggio 70", "Wolf 70"],
    "Super Star":  ["SS 70", "SS 100"],
}
COLORS = ["Black", "Red", "Blue", "White", "Silver", "Grey", "Green", "Orange"]
CONDITIONS = ["good", "damaged", "stripped"]


def _engine_number():
    """Generate a realistic Pakistani engine number."""
    prefix = random.choice(["PK", "E", "HND", "YMH", "SUZ"])
    year = random.randint(18, 24)
    digits = "".join([str(random.randint(0, 9)) for _ in range(7)])
    return f"{prefix}{year}{digits}"


def _chassis_number():
    chars = "ABCDEFGHJKLMNPRSTUVWXYZ0123456789"
    return "".join(random.choices(chars, k=17))


def _point_near(lat, lng, radius_deg=0.08):
    """Random point within ~9km of city centre."""
    return Point(
        lng + random.uniform(-radius_deg, radius_deg),
        lat + random.uniform(-radius_deg, radius_deg),
        srid=4326,
    )


class Command(BaseCommand):
    help = "Seed 100+ realistic demo theft/recovery records for ML demonstrations."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing seeded demo data before inserting",
        )
        parser.add_argument(
            "--count",
            type=int,
            default=120,
            help="Total number of theft reports to create (default: 120)",
        )

    def handle(self, *args, **options):
        from django.contrib.auth import get_user_model
        from apps.bikes.models import Bike
        from apps.reports.models import TheftReport, RecoveryRecord

        User = get_user_model()

        if options["clear"]:
            self.stdout.write("Clearing existing demo data…")
            RecoveryRecord.objects.all().delete()
            TheftReport.objects.all().delete()
            Bike.objects.all().delete()
            User.objects.filter(email__endswith="@demo.btt").delete()
            self.stdout.write(self.style.WARNING("Demo data cleared."))

        count = options["count"]
        self.stdout.write(f"Seeding {count} theft reports…")

        # ── Create demo users ──────────────────────────────────────────────────

        # 1 admin
        admin, _ = User.objects.get_or_create(
            email="admin@demo.btt",
            defaults=dict(full_name="Demo Admin", role="admin", is_verified=True, is_staff=True),
        )
        if _:
            admin.set_password("DemoAdmin@2024")
            admin.save()

        # 2 authority officers (one per major city)
        karachi_officer, _ = User.objects.get_or_create(
            email="authority.karachi@demo.btt",
            defaults=dict(
                full_name="Inspector Ali Raza", role="authority",
                badge_number="KHI-2024-001", city="Karachi", is_verified=True,
                cnic="4200011111111",
            ),
        )
        if _:
            karachi_officer.set_password("Authority@2024")
            karachi_officer.save()

        lahore_officer, _ = User.objects.get_or_create(
            email="authority.lahore@demo.btt",
            defaults=dict(
                full_name="Inspector Sara Khan", role="authority",
                badge_number="LHR-2024-002", city="Lahore", is_verified=True,
                cnic="3520022222222",
            ),
        )
        if _:
            lahore_officer.set_password("Authority@2024")
            lahore_officer.save()

        officers_by_city = {
            "Karachi": karachi_officer,
            "Lahore": lahore_officer,
        }

        # N owners — one per bike cluster
        owners = []
        for i in range(min(count // 2, 60)):
            city_name, city_lat, city_lng = random.choice(CITIES)
            email = f"owner{i:03d}@demo.btt"
            owner, created = User.objects.get_or_create(
                email=email,
                defaults=dict(
                    full_name=f"Demo Owner {i:03d}",
                    role="owner",
                    is_verified=True,
                    city=city_name,
                    phone=f"+92300{i:07d}",
                    cnic=f"{random.randint(1000000000000, 9999999999999)}",
                ),
            )
            if created:
                owner.set_password("Owner@2024")
                owner.save()
            owners.append(owner)

        # ── Create bikes + reports ─────────────────────────────────────────────

        reports_created = 0
        recovered_count = 0

        for i in range(count):
            owner = random.choice(owners)
            make = random.choice(MAKES)
            model = random.choice(MODELS[make])
            city_name, city_lat, city_lng = random.choice(CITIES)

            # Create bike
            engine = _engine_number()
            chassis = _chassis_number()

            # Skip if engine/chassis already exists (duplicate seed run)
            if Bike.objects.filter(engine_number=engine).exists():
                engine = engine + str(i)
            if Bike.objects.filter(chassis_number=chassis).exists():
                chassis = chassis[:15] + f"{i:02d}"

            bike = Bike.objects.create(
                owner=owner,
                make=make,
                model=model,
                year=random.randint(2015, 2024),
                color=random.choice(COLORS),
                engine_number=engine,
                chassis_number=chassis,
                registration_city=city_name,
            )

            # Theft date — within last 6 months
            days_ago = random.randint(1, 180)
            theft_date = date.today() - timedelta(days=days_ago)

            report = TheftReport.objects.create(
                bike=bike,
                reported_by=owner,
                theft_date=theft_date,
                theft_city=city_name,
                theft_location=_point_near(city_lat, city_lng),
                theft_location_detail=f"Near demo location in {city_name}",
                description="Demo theft report created by seed script.",
                status="stolen",
            )
            reports_created += 1

            # ~40% of reports get recovered
            if random.random() < 0.40:
                officer = officers_by_city.get(city_name, karachi_officer)
                recovery_days = random.randint(1, days_ago)
                recovery_city_name, rc_lat, rc_lng = random.choice(CITIES)

                RecoveryRecord.objects.create(
                    theft_report=report,
                    logged_by=officer,
                    recovery_date=theft_date + timedelta(days=recovery_days),
                    recovery_city=recovery_city_name,
                    recovery_location=_point_near(rc_lat, rc_lng, radius_deg=0.12),
                    bike_condition=random.choice(CONDITIONS),
                    notes="Demo recovery record created by seed script.",
                    fuzzy_match_score=round(random.uniform(75, 99), 2),
                )
                report.status = "recovered"
                report.save(update_fields=["status"])
                recovered_count += 1

        recovery_rate = round(recovered_count / reports_created * 100, 1) if reports_created else 0

        self.stdout.write(self.style.SUCCESS(
            f"\nDemo data seeded successfully!\n"
            f"  Theft reports: {reports_created}\n"
            f"  Recovered:     {recovered_count} ({recovery_rate}%)\n"
            f"  Owners:        {len(owners)}\n"
            f"\nDemo credentials:\n"
            f"  Admin:     admin@demo.btt          / DemoAdmin@2024\n"
            f"  Authority: authority.karachi@demo.btt / Authority@2024\n"
            f"  Authority: authority.lahore@demo.btt  / Authority@2024\n"
            f"  Owner:     owner000@demo.btt        / Owner@2024\n"
            f"\nNow run:\n"
            f"  python manage.py run_hotspot_analysis --all-cities\n"
            f"  python manage.py run_trend_analytics\n"
        ))
