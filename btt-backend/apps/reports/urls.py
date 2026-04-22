from django.urls import path
from .views import (
    TheftReportListCreateView,
    TheftReportDetailView,
    update_report_status,
    recovery_record,
    confirm_recovery_receipt,
)

urlpatterns = [
    path("", TheftReportListCreateView.as_view(), name="report-list-create"),
    path("<int:pk>/", TheftReportDetailView.as_view(), name="report-detail"),
    path("<int:pk>/status/", update_report_status, name="report-status-update"),
    path("<int:report_pk>/recovery/", recovery_record, name="recovery-record"),
    path("<int:report_pk>/recovery/confirm/", confirm_recovery_receipt, name="recovery-confirm"),
]
