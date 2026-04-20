"""
apps/reports/views.py
TheftReport and RecoveryRecord views.
Status update fires Django signal → notification engine.
"""
import logging
import threading
from django.db import transaction
from django.db.models import Q
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.users.permissions import (
    IsOwner,
    IsAuthority,
    IsAuthorityOrAdmin,
    IsAnyAuthenticatedRole,
    IsAdminUser,
)
from .models import TheftReport, RecoveryRecord
from .serializers import (
    TheftReportCreateSerializer,
    TheftReportListSerializer,
    TheftReportDetailSerializer,
    StatusUpdateSerializer,
    RecoveryCreateSerializer,
    RecoveryRecordSerializer,
)

logger = logging.getLogger(__name__)


class TheftReportListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/reports/  — Role-scoped list:
         Owner → own reports | Authority → city reports | Admin → all
    POST /api/reports/  — Owner files a new theft report
    """
    filterset_fields = ["status", "theft_city"]
    # reference_number is a @property — not a DB column — so it cannot be used in SearchFilter.
    search_fields = ["fir_number", "bike__engine_number", "bike__chassis_number"]
    ordering_fields = ["created_at", "theft_date", "status"]
    ordering = ["-created_at"]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsOwner()]
        return [IsAnyAuthenticatedRole()]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return TheftReportCreateSerializer
        return TheftReportListSerializer

    def get_queryset(self):
        user = self.request.user
        qs = TheftReport.objects.filter(deleted_at__isnull=True).select_related("bike")
        if user.is_owner:
            return qs.filter(reported_by=user)
        if user.is_authority:
            # Authority officers are scoped to their registered city.
            # If no city is configured on their account, return nothing
            # until an admin sets their city — prevents inadvertent data exposure.
            if not user.city:
                return qs.none()
            return qs.filter(theft_city__iexact=user.city)
        if user.is_admin:
            return qs
        # Community users cannot read full theft case data.
        return qs.none()

    def perform_create(self, serializer):
        report = serializer.save(reported_by=self.request.user)
        # Fire post-create notification in background
        threading.Thread(
            target=_notify_report_created,
            args=(report,),
            daemon=True,
        ).start()


class TheftReportDetailView(generics.RetrieveDestroyAPIView):
    """
    GET    /api/reports/{id}/  — Full report detail (authenticated)
    DELETE /api/reports/{id}/  — Admin soft-delete
    """
    serializer_class = TheftReportDetailSerializer

    def get_permissions(self):
        if self.request.method == "DELETE":
            return [IsAdminUser()]
        return [IsAnyAuthenticatedRole()]

    def get_queryset(self):
        user = self.request.user
        qs = TheftReport.objects.filter(deleted_at__isnull=True).select_related(
            "bike", "reported_by", "recovery"
        )
        if user.is_owner:
            return qs.filter(reported_by=user)
        if user.is_authority:
            if not user.city:
                return qs.none()
            return qs.filter(theft_city__iexact=user.city)
        if user.is_admin:
            return qs
        return qs.none()

    def destroy(self, request, *args, **kwargs):
        from django.utils import timezone
        report = self.get_object()
        report.deleted_at = timezone.now()
        report.save(update_fields=["deleted_at"])
        return Response(
            {"message": "Report soft-deleted. Evidence preserved."},
            status=status.HTTP_204_NO_CONTENT,
        )


@api_view(["PUT"])
@permission_classes([IsAuthorityOrAdmin])
def update_report_status(request, pk):
    """
    PUT /api/reports/{id}/status/
    Transitions report through the state machine:
    stolen → under_investigation → recovered → closed
    Triggers owner notification on every transition.
    """
    queryset = TheftReport.objects.filter(deleted_at__isnull=True)
    if request.user.is_authority:
        if not request.user.city:
            return Response({"error": "Your account has no city configured. Contact an admin."}, status=status.HTTP_403_FORBIDDEN)
        queryset = queryset.filter(theft_city__iexact=request.user.city)

    try:
        report = queryset.get(pk=pk)
    except TheftReport.DoesNotExist:
        return Response({"error": "Report not found."}, status=status.HTTP_404_NOT_FOUND)

    serializer = StatusUpdateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        old_status = report.transition_status(
            serializer.validated_data["status"],
            changed_by=request.user,
        )
    except ValueError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    threading.Thread(
        target=_notify_status_change,
        args=(report, old_status),
        daemon=True,
    ).start()

    return Response({
        "id": report.id,
        "reference_number": report.reference_number,
        "old_status": old_status,
        "new_status": report.status,
        "message": "Status updated successfully.",
    })


# ─── Recovery Record Views ─────────────────────────────────────────────────────

@api_view(["POST", "GET", "PUT"])
@permission_classes([IsAnyAuthenticatedRole])
def recovery_record(request, report_pk):
    """
    POST /api/reports/{id}/recovery/  — Authority logs a recovery
    GET  /api/reports/{id}/recovery/  — Retrieve recovery details
    PUT  /api/reports/{id}/recovery/  — Authority amends recovery record
    """
    queryset = TheftReport.objects.filter(deleted_at__isnull=True)
    if request.user.is_owner:
        queryset = queryset.filter(reported_by=request.user)
    elif request.user.is_authority:
        if not request.user.city:
            return Response({"error": "Your account has no city configured. Contact an admin."}, status=status.HTTP_403_FORBIDDEN)
        queryset = queryset.filter(theft_city__iexact=request.user.city)
    elif request.user.is_admin:
        pass
    else:
        queryset = queryset.none()

    try:
        report = queryset.get(pk=report_pk)
    except TheftReport.DoesNotExist:
        return Response({"error": "Report not found."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        if not hasattr(report, "recovery"):
            return Response({"error": "No recovery record for this report."}, status=status.HTTP_404_NOT_FOUND)
        # Owners see limited info — no officer contact details
        rec = report.recovery
        if request.user.is_owner:
            return Response({
                "recovery_date": rec.recovery_date,
                "recovery_city": rec.recovery_city,
                "bike_condition": rec.bike_condition,
            })
        return Response(RecoveryRecordSerializer(rec).data)

    if request.method == "POST":
        if not request.user.is_authority:
            return Response({"error": "Only Authority officers can log recoveries."}, status=status.HTTP_403_FORBIDDEN)
        if hasattr(report, "recovery"):
            return Response({"error": "This report already has a recovery record."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = RecoveryCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        if report.status != TheftReport.Status.UNDER_INVESTIGATION:
            return Response(
                {"error": "Recovery can only be logged when report is under investigation."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            recovery = serializer.save(theft_report=report, logged_by=request.user)
            report.transition_status(TheftReport.Status.RECOVERED, changed_by=request.user)

        threading.Thread(
            target=_notify_bike_recovered,
            args=(report, recovery),
            daemon=True,
        ).start()

        return Response(RecoveryRecordSerializer(recovery).data, status=status.HTTP_201_CREATED)

    if request.method == "PUT":
        if not request.user.is_authority:
            return Response({"error": "Only Authority officers can amend recovery records."}, status=status.HTTP_403_FORBIDDEN)
        if not hasattr(report, "recovery"):
            return Response({"error": "No recovery record to amend."}, status=status.HTTP_404_NOT_FOUND)

        serializer = RecoveryCreateSerializer(
            report.recovery, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        recovery = serializer.save()

        threading.Thread(
            target=_notify_recovery_amended,
            args=(report, recovery, request.user),
            daemon=True,
        ).start()

        return Response(RecoveryRecordSerializer(recovery).data)


# ─── Notification triggers ─────────────────────────────────────────────────────

def _notify_report_created(report):
    from apps.notifications.notification_service import notify_theft_reported
    try:
        notify_theft_reported(report)
    except Exception as exc:
        logger.error("Failed to send theft report notification: %s", exc)


def _notify_status_change(report, old_status):
    from apps.notifications.notification_service import notify_status_changed
    try:
        notify_status_changed(report, old_status)
    except Exception as exc:
        logger.error("Failed to send status change notification: %s", exc)


def _notify_bike_recovered(report, recovery):
    from apps.notifications.notification_service import notify_bike_recovered
    try:
        notify_bike_recovered(report, recovery)
    except Exception as exc:
        logger.error("Failed to send recovery notification: %s", exc)


def _notify_recovery_amended(report, recovery, officer):
    from apps.notifications.notification_service import notify_recovery_amended
    try:
        notify_recovery_amended(report, recovery, officer)
    except Exception as exc:
        logger.error("Failed to send recovery amendment notification: %s", exc)
