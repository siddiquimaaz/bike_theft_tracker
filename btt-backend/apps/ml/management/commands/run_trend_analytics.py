"""
apps/ml/management/commands/run_trend_analytics.py

Django management command — runs pandas trend aggregation.
Scheduled via OS cron: 0 3 * * 0 python manage.py run_trend_analytics

Usage:
    python manage.py run_trend_analytics
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Compute monthly theft/recovery trend analytics and cache results."

    def handle(self, *args, **options):
        from apps.ml.analysis import run_trend_analytics, save_trend_cache

        self.stdout.write("Running trend analytics…")

        try:
            result = run_trend_analytics()
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"Trend analytics FAILED: {exc}"))
            raise

        if "error" in result:
            self.stderr.write(self.style.ERROR(f"Trend analytics error: {result['error']}"))
            return

        record_count = result.get("record_count", 0)
        city_count = len(set(
            r["city"] for r in result.get("cities", [])
            if r["city"] != "__national__"
        ))

        save_trend_cache(result)

        self.stdout.write(
            self.style.SUCCESS(
                f"Trend analytics complete: {record_count} records, "
                f"{city_count} cities analysed. Cache TTL: 8 days."
            )
        )

        self._write_audit_log(record_count, city_count)

    @staticmethod
    def _write_audit_log(record_count: int, city_count: int):
        try:
            from django.contrib.auth import get_user_model
            from apps.users.models import AuditLog
            User = get_user_model()
            admin = User.objects.filter(role="admin", is_active=True).first()
            if admin:
                AuditLog.objects.create(
                    user=admin,
                    action="CRON_TREND_ANALYTICS",
                    table_affected="ml_analysis_cache",
                    new_value={"record_count": record_count, "city_count": city_count},
                )
        except Exception:
            pass
