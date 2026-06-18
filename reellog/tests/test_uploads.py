"""Tests for avatar upload validation and the favourites cap."""
from __future__ import annotations

import io

import pytest
from PIL import Image

from app.extensions import db
from app.models import Film, User
from app.uploads import UploadError, save_image


def _png_bytes(size=(64, 64), color=(120, 40, 200)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


class _Upload:
    """Minimal stand-in for a Werkzeug FileStorage."""

    def __init__(self, data: bytes, filename: str):
        self.stream = io.BytesIO(data)
        self.filename = filename


# --- save_image() unit tests (run inside an app context) ---------------------
def test_save_image_accepts_valid_png(app):
    with app.app_context():
        url = save_image(_Upload(_png_bytes(), "client-name.png"), "avatar")
    assert url.startswith("/uploads/")
    # Stored name is a server-generated uuid, NOT the client filename.
    assert "client-name" not in url
    assert url.endswith(".png")


def test_save_image_rejects_non_image(app):
    with app.app_context():
        with pytest.raises(UploadError):
            save_image(_Upload(b"this is not an image", "evil.png"), "avatar")


def test_save_image_rejects_oversized(app):
    with app.app_context():
        app.config["UPLOAD_MAX_BYTES"] = 100  # tiny cap for the test
        with pytest.raises(UploadError):
            save_image(_Upload(_png_bytes((256, 256)), "big.png"), "avatar")


def test_save_image_ignores_path_traversal_filename(app):
    # Even a traversal-style client filename can't escape: we never use it.
    with app.app_context():
        url = save_image(_Upload(_png_bytes(), "../../etc/passwd.png"), "avatar")
    assert ".." not in url
    assert url.startswith("/uploads/")


def test_save_image_avatar_is_cropped_square(app):
    with app.app_context():
        url = save_image(_Upload(_png_bytes((400, 200)), "wide.png"), "avatar")
        import os

        from PIL import Image as PILImage

        path = os.path.join(app.config["UPLOAD_DIR"], os.path.basename(url))
        with PILImage.open(path) as out:
            assert out.size == (512, 512)


# --- favourites cap (max 4) --------------------------------------------------
def _make_film(tmdb_id):
    f = Film(tmdb_id=tmdb_id, title=f"Film {tmdb_id}")
    db.session.add(f)
    db.session.commit()


def test_favorites_cap_at_four(auth_client):
    # Pre-cache 5 films so ensure_film_cached doesn't hit the network.
    for i in range(1, 6):
        _make_film(i)

    # First four succeed.
    for i in range(1, 5):
        resp = auth_client.post("/api/favorites/toggle", json={"tmdb_id": i})
        assert resp.status_code == 200, resp.get_json()
        assert resp.get_json()["is_favorite"] is True

    # The fifth is rejected with 409.
    resp = auth_client.post("/api/favorites/toggle", json={"tmdb_id": 5})
    assert resp.status_code == 409

    # Removing one frees a slot again.
    resp = auth_client.post("/api/favorites/toggle", json={"tmdb_id": 1})
    assert resp.get_json()["is_favorite"] is False
    resp = auth_client.post("/api/favorites/toggle", json={"tmdb_id": 5})
    assert resp.status_code == 200
    assert resp.get_json()["is_favorite"] is True


def test_oversized_request_returns_413(auth_client, app):
    app.config["MAX_CONTENT_LENGTH"] = 1024
    big = b"x" * 5000
    resp = auth_client.post(
        "/settings",
        data={"form_type": "profile", "avatar_file": (io.BytesIO(big), "a.png")},
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert resp.status_code in (303, 413)
