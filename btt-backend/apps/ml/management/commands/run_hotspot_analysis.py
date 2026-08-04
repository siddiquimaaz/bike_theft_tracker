"""
apps/ml/management/commands/run_hotspot_analysis.py

Django management command — runs DBSCAN hotspot clustering, corridor analysis,
and recovery radius statistics.  All three are cached and served by the ML API.

Scheduled via OS cron: 0 2 * * * python manage.py run_hotspot_analysis

Usage:
    python manage.py run_hotspot_analysis
    python manage.py run_hotspot_analysis --city Karachi
    python manage.py run_hotspot_analysis --all-cities
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = (
        "Run DBSCAN hotspot clustering, corridor analysis, and recovery radius "
        "on theft/recovery data and cache results for the ML dashboard."
    )

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
        from apps.ml.analysis import (
            run_hotspot_analysis, save_hotspot_cache,
            run_corridor_analysis, save_corridor_cache,
            run_recovery_radius, save_recovery_radius_cache,
        )
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
            self.stdout.write(f"Running analysis for {len(cities) - 1} cities + national…")
        else:
            cities = [city]

        # (label, run, save, skip-noun, success-line builder).  Only the hotspot
        # job counts toward success_count — it is the one the summary reports on.
        jobs = (
            (
                "Hotspot", run_hotspot_analysis, save_hotspot_cache, "records",
                lambda r: f"{len(r['clusters'])} clusters from {r['record_count']} records",
            ),
            (
                "Corridors", run_corridor_analysis, save_corridor_cache, "paired records",
                lambda r: (
                    f"{len(r['corridors'])} corridors "
                    f"from {r['record_count']} theft→recovery pairs"
                ),
            ),
            (
                "Radius", run_recovery_radius, save_recovery_radius_cache, "paired records",
                lambda r: (
                    f"mean={r['mean_km']} km, median={r['median_km']} km "
                    f"({r['record_count']} records)"
                ),
            ),
        )

        success_count = 0
        for target_city in cities:
            self.stdout.write(f"\n  ── {target_city or 'national'} ──")

            for name, run, save, skip_noun, describe in jobs:
                try:
                    result = run(city=target_city)
                    if result.get("skipped"):
                        self.stdout.write(self.style.WARNING(
                            f"    {name}: skipped "
                            f"({result['record_count']} {skip_noun} < minimum)"
                        ))
                        continue
                    save(result, city=target_city)
                    self.stdout.write(self.style.SUCCESS(f"    {name}: ✓ {describe(result)}"))
                    if name == "Hotspot":
                        success_count += 1
                except Exception as exc:
                    self.stderr.write(self.style.ERROR(f"    {name} FAILED: {exc}"))

        # Write completion to audit log
        self._write_audit_log(success_count, len(cities))
        self.stdout.write(self.style.SUCCESS(
            f"\nAnalysis complete: {success_count}/{len(cities)} hotspot scopes cached."
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
