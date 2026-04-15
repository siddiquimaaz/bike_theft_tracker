"""
apps/users/middleware.py
Audit logging middleware — records every successful state-changing request.
"""
import json
import logging

logger = logging.getLogger(__name__)

# Map HTTP methods to action verbs for the audit log
METHOD_ACTION_MAP = {
    "POST": "CREATED",
    "PUT": "UPDATED",
    "PATCH": "PATCHED",
    "DELETE": "DELETED",
}

# URL segments to table names
URL_TABLE_MAP = {
    "/api/bikes/": "bikes",
    "/api/reports/": "theft_reports",
    "/api/sightings/": "sighting_reports",
    "/api/notifications/": "notifications",
    "/api/admin/users/": "users",
}


def _resolve_table(path: str) -> str:
    for segment, table in URL_TABLE_MAP.items():
        if segment in path:
            return table
    return "unknown"


def _get_client_ip(request) -> str:
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


class AuditLoggingMiddleware:
    """
    Records POST / PUT / PATCH / DELETE requests that return 2xx to audit_logs.
    Non-blocking: if logging fails the request is NOT affected.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if (
            request.method in METHOD_ACTION_MAP
            and hasattr(request, "user")
            and request.user.is_authenticated
            and 200 <= response.status_code < 300
        ):
            try:
                self._write_audit(request, response)
            except Exception as exc:
                logger.error("AuditLoggingMiddleware failed: %s", exc, exc_info=True)

        return response

    def _write_audit(self, request, response):
        from apps.users.models import AuditLog

        action_prefix = METHOD_ACTION_MAP[request.method]
        table = _resolve_table(request.path)
        action = f"{action_prefix}_{table.upper()}"

        # Try to pull record ID from response body
        record_id = None
        new_value = None
        try:
            body = json.loads(response.content)
            record_id = body.get("id")
            new_value = {k: v for k, v in body.items() if k != "password_hash"}
        except Exception:
            pass

        AuditLog.objects.create(
            user=request.user,
            action=action,
            table_affected=table,
            record_id=record_id,
            new_value=new_value,
            ip_address=_get_client_ip(request),
        )
