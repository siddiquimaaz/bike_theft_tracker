"""
apps/common/uploads.py
Storage for user-supplied images (bike photos, recovery evidence, sighting photos).

Uploads are always stored under a generated UUID filename, never the client's:
the original name is attacker-controlled and would otherwise reach the
filesystem, and distinct users uploading "photo.jpg" must not collide.
"""
import os
import uuid

from django.conf import settings


def save_upload(uploaded_file, subdir: str) -> str:
    """
    Write `uploaded_file` into MEDIA_ROOT/<subdir>/ under a UUID filename,
    keeping the original extension.  Returns the stored filename alone (not the
    full path) — that is what the models persist.
    """
    ext = uploaded_file.name.rsplit(".", 1)[-1].lower()
    filename = f"{uuid.uuid4()}.{ext}"
    path = os.path.join(settings.MEDIA_ROOT, subdir, filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb+") as dest:
        for chunk in uploaded_file.chunks():
            dest.write(chunk)
    return filename


def save_uploads(uploaded_files, subdir: str) -> list[str]:
    """save_upload() over a list; returns the stored filenames in order."""
    return [save_upload(f, subdir) for f in uploaded_files]
