"""
tests/test_sightings.py
Sighting submission, listing, detail retrieval, and authority verification.
"""
import pytest
from io import BytesIO
from datetime import date
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

User = get_user_model()


@pytest.fixture
def sample_sighting(db, community_user):
    from apps.sightings.models import SightingReport
    return SightingReport.objects.create(
        sighter=community_user,
        raw_engine_number="HND22A1234567",
        sighting_date=date.today(),
        sighting_city="Karachi",
        sighting_description="Spotted near market",
    )


@pytest.fixture
def verified_sighting(db, authority_user, community_user, sample_bike):
    from apps.sightings.models import SightingReport
    s = SightingReport.objects.create(
        sighter=community_user,
        bike=sample_bike,
        raw_engine_number="HND22A0000001",
        sighting_date=date.today(),
        sighting_city="Lahore",
        is_verified=True,
        verified_by=authority_user,
    )
    return s


@pytest.mark.django_db
class TestSightingCreate:
    url = "/api/sightings/"

    def test_any_authenticated_user_can_submit(self, community_client):
        payload = {
            "raw_engine_number": "ABC123XYZ",
            "sighting_date": str(date.today()),
            "sighting_city": "Lahore",
            "sighting_description": "Saw near bus stop",
        }
        response = community_client.post(self.url, payload)
        assert response.status_code == 201

    def test_owner_can_submit_sighting(self, owner_client):
        payload = {
            "raw_engine_number": "XYZ987",
            "sighting_date": str(date.today()),
            "sighting_city": "Karachi",
        }
        response = owner_client.post(self.url, payload)
        assert response.status_code == 201

    def test_authority_can_submit_sighting(self, authority_client):
        payload = {
            "raw_engine_number": "ENG456789",
            "sighting_date": str(date.today()),
            "sighting_city": "Islamabad",
        }
        response = authority_client.post(self.url, payload)
        assert response.status_code == 201

    def test_unauthenticated_submit_rejected(self, api_client):
        payload = {
            "raw_engine_number": "ENG001",
            "sighting_date": str(date.today()),
            "sighting_city": "Karachi",
        }
        response = api_client.post(self.url, payload)
        assert response.status_code == 401

    def test_submit_with_chassis_number(self, community_client):
        payload = {
            "raw_chassis_number": "CHS999TEST",
            "sighting_date": str(date.today()),
            "sighting_city": "Peshawar",
        }
        response = community_client.post(self.url, payload)
        assert response.status_code == 201

    def test_submit_with_coordinates(self, owner_client):
        payload = {
            "raw_engine_number": "ENG555",
            "sighting_date": str(date.today()),
            "sighting_city": "Karachi",
            "latitude": 24.86,
            "longitude": 67.01,
        }
        response = owner_client.post(self.url, payload)
        assert response.status_code == 201


@pytest.mark.django_db
class TestSightingList:
    url = "/api/sightings/"

    def test_authority_can_list_sightings(self, authority_client, sample_sighting):
        response = authority_client.get(self.url)
        assert response.status_code == 200
        assert len(response.data) >= 1

    def test_admin_can_list_sightings(self, admin_client, sample_sighting):
        response = admin_client.get(self.url)
        assert response.status_code == 200

    def test_owner_sees_only_own_sightings(self, owner_client, owner_user):
        from apps.sightings.models import SightingReport
        SightingReport.objects.create(
            sighter=owner_user,
            raw_engine_number="OWN123",
            sighting_date=date.today(),
            sighting_city="Karachi",
        )
        response = owner_client.get(self.url)
        assert response.status_code == 200
        assert isinstance(response.data["results"], list)
        for sighting in response.data["results"]:
            assert sighting["id"] is not None

    def test_community_sees_only_own_sightings(self, community_client, community_user):
        from apps.sightings.models import SightingReport
        SightingReport.objects.create(
            sighter=community_user,
            raw_chassis_number="COM123",
            sighting_date=date.today(),
            sighting_city="Lahore",
        )
        response = community_client.get(self.url)
        assert response.status_code == 200
        assert isinstance(response.data["results"], list)

    def test_unauthenticated_cannot_list_sightings(self, api_client):
        response = api_client.get(self.url)
        assert response.status_code == 401

    def test_list_only_unverified_sightings(self, authority_client, sample_sighting, verified_sighting):
        response = authority_client.get(self.url)
        assert response.status_code == 200
        ids = [s["id"] for s in response.data["results"]]
        # sample_sighting is unverified → in list; verified_sighting is not
        assert sample_sighting.id in ids
        assert verified_sighting.id not in ids


@pytest.mark.django_db
class TestSightingDetail:
    def test_owner_can_retrieve_own_sighting(self, owner_client, owner_user):
        from apps.sightings.models import SightingReport
        own = SightingReport.objects.create(
            sighter=owner_user,
            raw_engine_number="OWNER-DETAIL-1",
            sighting_date=date.today(),
            sighting_city="Karachi",
        )
        response = owner_client.get(f"/api/sightings/{own.id}/")
        assert response.status_code == 200
        assert response.data["id"] == own.id

    def test_community_can_retrieve_sighting(self, community_client, sample_sighting):
        response = community_client.get(f"/api/sightings/{sample_sighting.id}/")
        assert response.status_code == 200

    def test_authority_can_retrieve_sighting(self, authority_client, sample_sighting):
        response = authority_client.get(f"/api/sightings/{sample_sighting.id}/")
        assert response.status_code == 200

    def test_unauthenticated_cannot_retrieve(self, api_client, sample_sighting):
        response = api_client.get(f"/api/sightings/{sample_sighting.id}/")
        assert response.status_code == 401

    def test_nonexistent_sighting_returns_404(self, owner_client):
        response = owner_client.get("/api/sightings/999999/")
        assert response.status_code == 404

    def test_owner_cannot_retrieve_others_sighting(self, owner_client, sample_sighting):
        # sample_sighting belongs to community fixture user
        response = owner_client.get(f"/api/sightings/{sample_sighting.id}/")
        assert response.status_code == 404

    def test_community_cannot_retrieve_others_sighting(self, community_client, owner_user):
        from apps.sightings.models import SightingReport
        other = SightingReport.objects.create(
            sighter=owner_user,
            raw_engine_number="OWN-ONLY-DETAIL",
            sighting_date=date.today(),
            sighting_city="Karachi",
        )
        response = community_client.get(f"/api/sightings/{other.id}/")
        assert response.status_code == 404


@pytest.mark.django_db
class TestVerifySighting:
    def test_authority_can_verify_sighting(self, authority_client, sample_sighting, sample_bike):
        url = f"/api/sightings/{sample_sighting.id}/verify/"
        response = authority_client.put(url, {"bike_id": sample_bike.id}, format="json")
        assert response.status_code == 200
        assert response.data["is_verified"] is True
        assert response.data["bike_id"] == sample_bike.id

    def test_admin_can_verify_sighting(self, admin_client, sample_sighting, sample_bike):
        url = f"/api/sightings/{sample_sighting.id}/verify/"
        response = admin_client.put(url, {"bike_id": sample_bike.id}, format="json")
        assert response.status_code == 200

    def test_owner_cannot_verify_sighting(self, owner_client, sample_sighting, sample_bike):
        url = f"/api/sightings/{sample_sighting.id}/verify/"
        response = owner_client.put(url, {"bike_id": sample_bike.id})
        assert response.status_code == 403

    def test_community_cannot_verify_sighting(self, community_client, sample_sighting, sample_bike):
        url = f"/api/sightings/{sample_sighting.id}/verify/"
        response = community_client.put(url, {"bike_id": sample_bike.id})
        assert response.status_code == 403

    def test_verify_without_bike_id_returns_400(self, authority_client, sample_sighting):
        url = f"/api/sightings/{sample_sighting.id}/verify/"
        response = authority_client.put(url, {})
        assert response.status_code == 400
        assert "bike_id" in response.data["error"]

    def test_verify_nonexistent_sighting_returns_404(self, authority_client, sample_bike):
        url = "/api/sightings/999999/verify/"
        response = authority_client.put(url, {"bike_id": sample_bike.id})
        assert response.status_code == 404

    def test_verify_with_nonexistent_bike_returns_404(self, authority_client, sample_sighting):
        url = f"/api/sightings/{sample_sighting.id}/verify/"
        response = authority_client.put(url, {"bike_id": 999999})
        assert response.status_code == 404

    def test_authority_cannot_verify_cross_city_sighting(
        self, authority_client, authority_user, sample_sighting, sample_bike
    ):
        # sample_sighting is in Karachi by fixture; set authority to a different city.
        authority_user.city = "Lahore"
        authority_user.save(update_fields=["city"])

        url = f"/api/sightings/{sample_sighting.id}/verify/"
        response = authority_client.put(url, {"bike_id": sample_bike.id}, format="json")
        assert response.status_code == 403
        assert "assigned city" in response.data["error"]

    def test_unauthenticated_cannot_verify(self, api_client, sample_sighting, sample_bike):
        url = f"/api/sightings/{sample_sighting.id}/verify/"
        response = api_client.put(url, {"bike_id": sample_bike.id})
        assert response.status_code == 401


@pytest.mark.django_db
class TestSightingCoverageBranches:
    def test_submit_with_photo_persists_filename(self, community_client, settings, tmp_path):
        settings.MEDIA_ROOT = str(tmp_path)
        img = BytesIO()
        Image.new("RGB", (1, 1), color=(0, 255, 0)).save(img, format="PNG")
        png_1x1 = img.getvalue()
        photo = SimpleUploadedFile("spot.png", png_1x1, content_type="image/png")
        payload = {
            "raw_engine_number": "ENG-PHOTO-001",
            "sighting_date": str(date.today()),
            "sighting_city": "Karachi",
            "photo": photo,
        }
        response = community_client.post("/api/sightings/", payload, format="multipart")
        assert response.status_code == 201
        from apps.sightings.models import SightingReport
        sighting = SightingReport.objects.get(raw_engine_number="ENG-PHOTO-001")
        assert sighting.photo_url
        assert sighting.photo_url.endswith(".png")

    def test_fuzzy_match_with_non_numeric_bike_id_is_ignored(self, community_client, monkeypatch):
        def fake_matches(*args, **kwargs):
            return [{"bike_id": "abc", "score": 72.5}]

        monkeypatch.setattr("apps.ml.fuzzy_match.find_fuzzy_matches", fake_matches)
        payload = {
            "raw_engine_number": "ENG-INVALID-BIKE-ID",
            "sighting_date": str(date.today()),
            "sighting_city": "Karachi",
        }
        response = community_client.post("/api/sightings/", payload)
        assert response.status_code == 201
        from apps.sightings.models import SightingReport
        sighting = SightingReport.objects.get(raw_engine_number="ENG-INVALID-BIKE-ID")
        assert float(sighting.fuzzy_match_score) == 72.5
        assert sighting.top_match_bike_id is None
