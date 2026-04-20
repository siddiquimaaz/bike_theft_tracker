"""
tests/test_reports.py
TheftReport lifecycle, state machine, recovery record, and RBAC tests.
"""
import pytest
from datetime import date


@pytest.mark.django_db
class TestTheftReportSubmission:
    url = "/api/reports/"

    def test_owner_can_file_report(self, owner_client, sample_bike):
        payload = {
            "bike": sample_bike.id,
            "theft_date": str(date.today()),
            "theft_city": "Karachi",
        }
        response = owner_client.post(self.url, payload)
        assert response.status_code == 201
        assert "reference_number" in response.data
        assert response.data["reference_number"].startswith("BTT-")

    def test_future_theft_date_rejected(self, owner_client, sample_bike):
        from datetime import timedelta
        payload = {
            "bike": sample_bike.id,
            "theft_date": str(date.today() + timedelta(days=1)),
            "theft_city": "Karachi",
        }
        response = owner_client.post(self.url, payload)
        assert response.status_code == 400

    def test_cannot_report_other_owners_bike(self, owner_client, owner_user_2, db):
        from apps.bikes.models import Bike
        other_bike = Bike.objects.create(
            owner=owner_user_2, make="Honda", model="CD 70", year=2020,
            engine_number="OTHERBIKE00001", chassis_number="OTHERBIKECHASSIS1",
        )
        payload = {"bike": other_bike.id, "theft_date": str(date.today()), "theft_city": "Lahore"}
        response = owner_client.post(self.url, payload)
        assert response.status_code == 400

    def test_cannot_file_duplicate_report(self, owner_client, sample_bike, sample_report):
        payload = {
            "bike": sample_bike.id,
            "theft_date": str(date.today()),
            "theft_city": "Karachi",
        }
        response = owner_client.post(self.url, payload)
        assert response.status_code == 400
        assert "active theft report" in str(response.data).lower()

    def test_authority_cannot_file_report(self, authority_client, sample_bike):
        payload = {
            "bike": sample_bike.id,
            "theft_date": str(date.today()),
            "theft_city": "Karachi",
        }
        response = authority_client.post(self.url, payload)
        assert response.status_code == 403

    def test_unauthenticated_request_rejected(self, api_client):
        response = api_client.post(self.url, {})
        assert response.status_code == 401


@pytest.mark.django_db
class TestReportVisibility:
    def test_owner_sees_own_reports(self, owner_client, sample_report):
        response = owner_client.get("/api/reports/")
        assert response.status_code == 200
        ids = [r["id"] for r in response.data["results"]]
        assert sample_report.id in ids

    def test_authority_sees_city_reports(self, authority_client, sample_report):
        # authority_user.city = "Karachi", sample_report.theft_city = "Karachi"
        response = authority_client.get("/api/reports/")
        assert response.status_code == 200
        ids = [r["id"] for r in response.data["results"]]
        assert sample_report.id in ids

    def test_admin_sees_all_reports(self, admin_client, sample_report):
        response = admin_client.get("/api/reports/")
        assert response.status_code == 200
        ids = [r["id"] for r in response.data["results"]]
        assert sample_report.id in ids

    def test_community_cannot_list_reports(self, community_client):
        response = community_client.get("/api/reports/")
        assert response.status_code == 200
        assert response.data["count"] == 0

    def test_community_cannot_view_report_detail(self, community_client, sample_report):
        response = community_client.get(f"/api/reports/{sample_report.id}/")
        assert response.status_code == 404


@pytest.mark.django_db
class TestStatusTransition:
    def test_authority_can_advance_status(self, authority_client, sample_report):
        url = f"/api/reports/{sample_report.id}/status/"
        response = authority_client.put(url, {"status": "under_investigation"})
        assert response.status_code == 200
        assert response.data["new_status"] == "under_investigation"

    def test_invalid_status_transition_rejected(self, authority_client, sample_report):
        # Cannot jump directly from stolen → recovered
        url = f"/api/reports/{sample_report.id}/status/"
        response = authority_client.put(url, {"status": "recovered"})
        assert response.status_code == 400

    def test_owner_cannot_update_status(self, owner_client, sample_report):
        url = f"/api/reports/{sample_report.id}/status/"
        response = owner_client.put(url, {"status": "under_investigation"})
        assert response.status_code == 403

    def test_authority_cannot_update_other_city_report(
        self, authority_client_lahore, sample_report
    ):
        url = f"/api/reports/{sample_report.id}/status/"
        response = authority_client_lahore.put(url, {"status": "under_investigation"})
        assert response.status_code == 404


@pytest.mark.django_db
class TestRecoveryRecord:
    def test_authority_can_log_recovery(self, authority_client, sample_report):
        # First advance to under_investigation
        sample_report.status = "under_investigation"
        sample_report.save(update_fields=["status"])

        url = f"/api/reports/{sample_report.id}/recovery/"
        payload = {
            "recovery_date": str(date.today()),
            "recovery_city": "Karachi",
            "bike_condition": "good",
        }
        response = authority_client.post(url, payload)
        assert response.status_code == 201
        assert response.data["recovery_city"] == "Karachi"

    def test_duplicate_recovery_rejected(self, authority_client, recovered_report):
        url = f"/api/reports/{recovered_report.id}/recovery/"
        payload = {
            "recovery_date": str(date.today()),
            "recovery_city": "Lahore",
            "bike_condition": "damaged",
        }
        response = authority_client.post(url, payload)
        assert response.status_code == 400

    def test_recovery_rejected_when_report_not_under_investigation(
        self, authority_client, sample_report
    ):
        url = f"/api/reports/{sample_report.id}/recovery/"
        payload = {
            "recovery_date": str(date.today()),
            "recovery_city": "Karachi",
            "bike_condition": "good",
        }
        response = authority_client.post(url, payload)
        assert response.status_code == 400

    def test_owner_gets_limited_recovery_view(self, owner_client, recovered_report):
        url = f"/api/reports/{recovered_report.id}/recovery/"
        response = owner_client.get(url)
        assert response.status_code == 200
        # Owner should NOT see officer contact or full details
        assert "logged_by_id" not in response.data
        assert "recovery_city" in response.data

    def test_community_cannot_get_recovery_record(self, community_client, recovered_report):
        url = f"/api/reports/{recovered_report.id}/recovery/"
        response = community_client.get(url)
        assert response.status_code == 404
