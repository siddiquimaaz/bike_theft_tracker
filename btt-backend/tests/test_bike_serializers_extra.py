import pytest
from io import BytesIO
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.bikes.serializers import BikeCreateSerializer, BikeUpdateSerializer


def _png_1x1_bytes():
    buf = BytesIO()
    Image.new("RGB", (1, 1), color=(255, 0, 0)).save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.django_db
class TestBikeSerializersExtra:
    def test_create_serializer_saves_uploaded_photo(self, owner_user, settings, tmp_path, monkeypatch):
        settings.MEDIA_ROOT = str(tmp_path)
        monkeypatch.setattr("apps.bikes.serializers.magic.from_buffer", lambda *_a, **_k: "image/png")

        photo = SimpleUploadedFile("bike.png", _png_1x1_bytes(), content_type="image/png")
        serializer = BikeCreateSerializer(data={
            "make": "Honda",
            "model": "CD70",
            "year": 2020,
            "color": "Black",
            "engine_number": "eng-new-001",
            "chassis_number": "chs-new-001",
            "photo": photo,
        })
        assert serializer.is_valid(), serializer.errors
        bike = serializer.save(owner=owner_user)
        assert bike.photo_url
        assert bike.photo_url.endswith(".png")

    def test_update_serializer_replaces_photo(self, sample_bike, settings, tmp_path):
        settings.MEDIA_ROOT = str(tmp_path)
        photo = SimpleUploadedFile("bike2.png", _png_1x1_bytes(), content_type="image/png")
        serializer = BikeUpdateSerializer(
            instance=sample_bike,
            data={"color": "Blue", "photo": photo},
            partial=True,
        )
        assert serializer.is_valid(), serializer.errors
        updated = serializer.save()
        assert updated.color == "Blue"
        assert updated.photo_url
        assert updated.photo_url.endswith(".png")
