"""
apps/ml/management/commands/run_hotspot_analysis.py

Django management command — runs DBSCAN hotspot clustering.
Scheduled via OS cron: 0 2 * * * python manage.py run_hotspot_analysis

Usage:
    python manage.py run_hotspot_analysis
    python manage.py run_hotspot_analysis --city Karachi
    python manage.py run_hotspot_analysis --all-cities
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = "Run DBSCAN hotspot clustering on theft report locations and cache results."

    def add_arguments(self, parser):
        parser.add_argument(
            "--city",
            type=str,
            default=None,
            help="Scope analysis to a specific city (default: national)",
        )
        parser.add_argument(
            "--all-cities",
            action="store_true",
            help="Run analysis for every city that has theft reports, plus national",
        )

    def handle(self, *args, **options):
        from apps.ml.analysis import run_hotspot_analysis, save_hotspot_cache
        from apps.reports.models import TheftReport

        city = options.get("city")
        all_cities = options.get("all_cities")

        if all_cities:
            cities = list(
                TheftReport.objects.filter(deleted_at__isnull=True)
                .values_list("theft_city", flat=True)
                .distinct()
            )
            cities.append(None)  # None = national
            self.stdout.write(f"Running analysis for {len(cities)} cities + national…")
        else:
            cities = [city]

        success_count = 0
        for target_city in cities:
            label = target_city or "national"
            self.stdout.write(f"  Analysing [{label}]…")
            try:
                result = run_hotspot_analysis(city=target_city)
                if result.get("skipped"):
                    self.stdout.write(
                        self.style.WARNING(
                            f"  [{label}] Skipped — only {result['record_count']} records "
                            f"(minimum required: 10)"
                        )
                    )
                else:
                    save_hotspot_cache(result, city=target_city)
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  [{label}] ✓ {len(result['clusters'])} clusters "
                            f"from {result['record_count']} records "
                            f"({result['noise_points']} noise points)"
                        )
                    )
                    success_count += 1
            except Exception as exc:
                self.stderr.write(
                    self.style.ERROR(f"  [{label}] FAILED: {exc}")
                )

        # Write completion to audit log
        self._write_audit_log(success_count, len(cities))
        self.stdout.write(self.style.SUCCESS(
            f"\nHotspot analysis complete: {success_count}/{len(cities)} scopes succeeded."
        ))

    @staticmethod
    def _write_audit_log(success_count: int, total: int):
        """Record cron job run in audit_logs using the system admin account."""
        try:
            from apps.users.models import AuditLog
            User = get_user_model()
            admin = User.objects.filter(role="admin", is_active=True).first()
            if admin:
                AuditLog.objects.create(
                    user=admin,
                    action="CRON_HOTSPOT_ANALYSIS",
                    table_affected="ml_analysis_cache",
                    new_value={"success": success_count, "total": total},
                )
        except Exception:
            pass  # Audit log failure must never crash the cron job
