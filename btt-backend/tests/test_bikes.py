"""
tests/test_bikes.py
Bike registration, update, delete, and public search endpoint tests.
"""
import pytest


@pytest.mark.django_db
class TestBikeRegistration:
    url = "/api/bikes/"

    def test_owner_can_register_bike(self, owner_client):
        payload = {
            "make": "Honda",
            "model": "CG 125",
            "year": 2022,
            "color": "Black",
            "engine_number": "HND22NEW00001",
            "chassis_number": "MRHGC1250NY000001",
        }
        response = owner_client.post(self.url, payload)
        assert response.status_code == 201
        assert response.data["engine_number"] == "HND22NEW00001"

    def test_engine_number_normalized_to_uppercase(self, owner_client):
        payload = {
            "make": "Yamaha", "model": "YBR 125", "year": 2021,
            "engine_number": "ybr21lower00001",
            "chassis_number": "YBR21CHASSIS0001",
        }
        response = owner_client.post(self.url, payload)
        assert response.status_code == 201
        assert response.data["engine_number"] == "YBR21LOWER00001"

    def test_non_owner_cannot_register_bike(self, authority_client):
        payload = {
            "make": "Honda", "model": "CD 70", "year": 2020,
            "engine_number": "FORBID0000001",
            "chassis_number": "FORBIDCHASSIS001",
        }
        response = authority_client.post(self.url, payload)
        assert response.status_code == 403

    def test_duplicate_engine_number_rejected(self, owner_client, sample_bike):
        payload = {
            "make": "Honda", "model": "CD 70", "year": 2019,
            "engine_number": sample_bike.engine_number,  # duplicate
            "chassis_number": "UNIQUECHASSIS0001",
        }
        response = owner_client.post(self.url, payload)
        assert response.status_code == 400

    def test_unauthenticated_request_rejected(self, api_client):
        response = api_client.post(self.url, {})
        assert response.status_code == 401


@pytest.mark.django_db
class TestBikeList:
    def test_owner_sees_only_own_bikes(self, owner_client, owner_user_2, sample_bike, db):
        from apps.bikes.models import Bike
        # Bike belonging to owner_2 — should NOT appear in owner_client's list
        Bike.objects.create(
            owner=owner_user_2, make="Yamaha", model="YBR 125", year=2021,
            engine_number="OTHER00000001", chassis_number="OTHERCHASSIS0001",
        )
        response = owner_client.get("/api/bikes/")
        assert response.status_code == 200
        ids_returned = [b["id"] for b in response.data["results"]]
        assert sample_bike.id in ids_returned
        # Other owner's bike must NOT be in results
        other_bike = Bike.objects.get(engine_number="OTHER00000001")
        assert other_bike.id not in ids_returned


@pytest.mark.django_db
class TestBikeUpdate:
    def test_owner_can_update_color(self, owner_client, sample_bike):
        url = f"/api/bikes/{sample_bike.id}/"
        response = owner_client.put(url, {"color": "Red"})
        assert response.status_code == 200

    def test_engine_number_is_immutable(self, owner_client, sample_bike):
        """PUT with engine_number is silently ignored — field not in UpdateSerializer."""
        url = f"/api/bikes/{sample_bike.id}/"
        original_engine = sample_bike.engine_number
        owner_client.put(url, {"engine_number": "HACKED00000001", "color": "Blue"})
        sample_bike.refresh_from_db()
        assert sample_bike.engine_number == original_engine


@pytest.mark.django_db
class TestBikeDelete:
    def test_owner_can_soft_delete_bike(self, owner_client, sample_bike):
        url = f"/api/bikes/{sample_bike.id}/"
        response = owner_client.delete(url)
        assert response.status_code == 204
        sample_bike.refresh_from_db()
        assert sample_bike.deleted_at is not None

    def test_cannot_delete_bike_with_active_report(self, owner_client, sample_report, sample_bike):
        url = f"/api/bikes/{sample_bike.id}/"
        response = owner_client.delete(url)
        assert response.status_code == 400
        assert "active theft report" in response.data["error"].lower()


@pytest.mark.django_db
class TestPublicSearch:
    def test_search_by_engine_number(self, api_client, sample_bike):
        response = api_client.get(f"/api/search/bike/?q={sample_bike.engine_number[:8]}")
        assert response.status_code == 200
        assert response.data["count"] >= 1

    def test_search_too_short_query(self, api_client):
        response = api_client.get("/api/search/bike/?q=AB")
        assert response.status_code == 400

    def test_stolen_bike_flagged(self, api_client, sample_bike, sample_report):
        response = api_client.get(f"/api/search/bike/?q={sample_bike.engine_number}")
        assert response.status_code == 200
        results = response.data["results"]
        assert len(results) == 1
        assert results[0]["status"] == "REPORTED STOLEN"

    def test_no_owner_data_in_public_search(self, api_client, sample_bike, sample_report):
        response = api_client.get(f"/api/search/bike/?q={sample_bike.engine_number}")
        result = response.data["results"][0]
        assert "owner" not in result
        assert "email" not in result
        assert "phone" not in result

    def test_city_report_count(self, api_client, sample_report):
        response = api_client.get("/api/search/city/Karachi/")
        assert response.status_code == 200
        assert response.data["active_theft_reports"] >= 1
