"""Admin URL patterns — /api/admin/"""
from django.urls import path
from apps.users.views.admin_views import (
    UserListView,
    CreateAuthorityView,
    UserStatusUpdateView,
    UserDeleteView,
    analytics_overview,
    AuditLogListView,
)

urlpatterns = [
    path("users/", UserListView.as_view(), name="admin-users-list"),
    path("users/authority/", CreateAuthorityView.as_view(), name="admin-create-authority"),
    path("users/<int:pk>/status/", UserStatusUpdateView.as_view(), name="admin-user-status"),
    path("users/<int:pk>/", UserDeleteView.as_view(), name="admin-user-delete"),
    path("analytics/", analytics_overview, name="admin-analytics"),
    path("audit-logs/", AuditLogListView.as_view(), name="admin-audit-logs"),
]
