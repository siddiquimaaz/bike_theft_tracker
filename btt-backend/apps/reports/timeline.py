from apps.reports.models import CaseTimeline


def add_case_timeline_event(report, action, actor=None, metadata=None):
    if report is None:
        return None
    return CaseTimeline.objects.create(
        theft_report=report,
        actor=actor,
        action=action,
        metadata=metadata or {},
    )
