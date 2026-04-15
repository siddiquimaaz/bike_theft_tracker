"""
apps/notifications/views.py
In-app notification list and read-status management.
Frontend polls GET /api/notifications/ every 30s for new notifications.
"""
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import serializers

from apps.users.permissions import IsAnyAuthenticatedRole
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id", "type", "message", "is_read",
            "delivery_channel", "report_id", "created_at",
        ]


class NotificationListView(generics.ListAPIView):
    """
    GET /api/notifications/
    All notifications for authenticated user — unread count in header.
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAnyAuthenticatedRole]
    filterset_fields = ["is_read", "type"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        unread_count = Notification.objects.filter(
            user=request.user, is_read=False
        ).count()
        # response.data is a list from ListAPIView — wrap it in a dict
        # so we can include unread_count alongside the results.
        response.data = {
            "unread_count": unread_count,
            "results": response.data,
        }
        return response


@api_view(["PUT"])
@permission_classes([IsAnyAuthenticatedRole])
def mark_notification_read(request, pk):
    """PUT /api/notifications/{id}/read/ — Mark single notification as read."""
    try:
        notification = Notification.objects.get(pk=pk, user=request.user)
    except Notification.DoesNotExist:
        return Response({"error": "Notification not found."}, status=status.HTTP_404_NOT_FOUND)

    notification.is_read = True
    notification.save(update_fields=["is_read"])
    return Response({"id": pk, "is_read": True})


@api_view(["PUT"])
@permission_classes([IsAnyAuthenticatedRole])
def mark_all_notifications_read(request):
    """PUT /api/notifications/read-all/ — Mark all user notifications as read."""
    updated = Notification.objects.filter(
        user=request.user, is_read=False
    ).update(is_read=True)
    return Response({"message": f"{updated} notifications marked as read."})
