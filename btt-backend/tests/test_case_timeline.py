import pytest

from apps.reports.models import CaseTimeline


@pytest.mark.django_db
def test_case_timeline_basic(sample_report, owner_user):
    CaseTimeline.objects.create(theft_report=sample_report, actor=owner_user, action="reported", metadata={"note": "test"})
    entries = sample_report.timeline.all()
    assert entries.count() == 1
    assert entries[0].action == "reported"
