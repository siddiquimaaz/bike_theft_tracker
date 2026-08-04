"""
apps/users/views/admin_views.py
Admin-only endpoints: user management, analytics overview, audit log.
"""
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.common.background import background_task, run_in_background
from apps.users.models import AuditLog
from apps.users.permissions import IsAdminUser
from apps.users.serializers import (
    AuthorityCreationSerializer,
    UserListSerializer,
    UserStatusUpdateSerializer,
)

User = get_user_model()


class UserListView(generics.ListAPIView):
    """
    GET /api/admin/users/
    List all users. Filters: role, city, is_verified, is_active.
    """
    serializer_class = UserListSerializer
    permission_classes = [IsAdminUser]
    filterset_fields = ["role", "city", "is_verified", "is_active"]
    search_fields = ["full_name", "email", "cnic"]
    ordering_fields = ["created_at", "full_name"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return User.objects.filter(deleted_at__isnull=True)


class CreateAuthorityView(generics.CreateAPIView):
    """
    POST /api/admin/users/authority/
    Admin creates a police authority account with badge_number + CNIC.
    Auto-sends credential email to the new officer.
    """
    serializer_class = AuthorityCreationSerializer
    permission_classes = [IsAdminUser]

    def perform_create(self, serializer):
        user = serializer.save()
        run_in_background(self._send_credentials_email, user)

    @staticmethod
    @background_task("Failed to send authority credentials email: %s")
    def _send_credentials_email(user):
        from apps.notifications.email_service import send_authority_credentials_email
        send_authority_credentials_email(user)


class UserStatusUpdateView(generics.UpdateAPIView):
    """
    PUT /api/admin/users/{id}/status/
    Activate, deactivate, or change user role.
    """
    serializer_class = UserStatusUpdateSerializer
    permission_classes = [IsAdminUser]
    queryset = User.objects.all()

    def update(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = self.get_serializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "User status updated.", "user": UserListSerializer(user).data})


class UserDeleteView(generics.DestroyAPIView):
    """
    DELETE /api/admin/users/{id}/
    Soft-delete any user (owner/authority/community/admin) by setting deleted_at
    and deactivating the account.
    """
    permission_classes = [IsAdminUser]
    queryset = User.objects.all()

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        user.deleted_at = timezone.now()
        user.is_active = False
        user.save(update_fields=["deleted_at", "is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([IsAdminUser])
def analytics_overview(request):
    """
    GET /api/admin/analytics/
    Real-time dashboard KPIs — report counts by status, recovery rate, city breakdown.
    """
    from apps.reports.models import TheftReport
    from apps.sightings.models import SightingReport

    report_stats = TheftReport.objects.filter(deleted_at__isnull=True).aggregate(
        total=Count("id"),
        stolen=Count("id", filter=Q(status="stolen")),
        under_investigation=Count("id", filter=Q(status="under_investigation")),
        recovered=Count("id", filter=Q(status="recovered")),
        closed=Count("id", filter=Q(status="closed")),
    )

    total = report_stats["total"] or 1  # Avoid division by zero
    recovery_rate = round((report_stats["recovered"] / total) * 100, 2)

    city_breakdown = (
        TheftReport.objects.filter(deleted_at__isnull=True)
        .values("theft_city")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    user_stats = User.objects.aggregate(
        total_users=Count("id"),
        owners=Count("id", filter=Q(role="owner")),
        authorities=Count("id", filter=Q(role="authority")),
        community=Count("id", filter=Q(role="community")),
    )

    from apps.ml.models import MLAnalysisCache
    ml_cache = MLAnalysisCache.objects.filter(
        expires_at__gt=timezone.now()
    ).values("analysis_type", "computed_at", "record_count")

    return Response({
        "reports": {**report_stats, "recovery_rate_pct": recovery_rate},
        "city_breakdown": list(city_breakdown),
        "users": user_stats,
        "unverified_sightings": SightingReport.objects.filter(is_verified=False).count(),
        "ml_cache_status": list(ml_cache),
    })


class AuditLogListView(generics.ListAPIView):
    """
    GET /api/admin/audit-logs/
    Immutable audit log viewer. Filters: user, action, table_affected, date range.
    """
    permission_classes = [IsAdminUser]
    filterset_fields = ["user", "action", "table_affected"]
    search_fields = ["action", "table_affected"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return AuditLog.objects.select_related("user").all()

    def get_serializer_class(self):
        from rest_framework import serializers

        class AuditLogSerializer(serializers.ModelSerializer):
            # user may be NULL when the associated account was deleted (SET_NULL cascade)
            user_email = serializers.SerializerMethodField()

            def get_user_email(self, obj):
                return obj.user.email if obj.user_id and obj.user else "[deleted]"

            class Meta:
                model = AuditLog
                fields = "__all__"

        return AuditLogSerializer
