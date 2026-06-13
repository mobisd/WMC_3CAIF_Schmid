"""Image upload handling for avatars and profile backdrops.

Security posture:
- We never trust the client-supplied filename or Content-Type. The stored name
  is a fresh ``uuid4`` + an extension derived from the *actual* image format
  detected by Pillow, so path traversal and content-type spoofing are
  impossible.
- Files are validated (it must really decode as JPEG/PNG/WEBP), size-capped,
  and re-encoded (which strips metadata and any smuggled payload).
- Avatars are centre-cropped to a square; backdrops are downscaled — keeps
  storage sane and the UI consistent.
"""
from __future__ import annotations

import os
import uuid
from typing import Optional

from flask import current_app
from PIL import Image, ImageOps, UnidentifiedImageError

# Pillow format name -> stored extension. Mirrors Config.ALLOWED_IMAGE_TYPES.
_FORMAT_EXT = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}

AVATAR_SIZE = (512, 512)
BACKDROP_MAX = (1600, 900)


class UploadError(ValueError):
    """Raised for any invalid upload; the message is safe to show the user."""


def _file_size(file_storage) -> int:
    stream = file_storage.stream
    pos = stream.tell()
    stream.seek(0, os.SEEK_END)
    size = stream.tell()
    stream.seek(pos)
    return size


def save_image(file_storage, kind: str) -> str:
    """Validate, process and store an uploaded image.

    ``kind`` is ``"avatar"`` or ``"backdrop"``. Returns the relative URL
    (``/uploads/<name>``) to store on the user. Raises ``UploadError`` on any
    invalid input.
    """
    if file_storage is None or not file_storage.filename:
        raise UploadError("No file was selected.")

    max_bytes = current_app.config["UPLOAD_MAX_BYTES"]
    if _file_size(file_storage) > max_bytes:
        mb = max_bytes // (1024 * 1024)
        raise UploadError(f"Image is too large (max {mb} MB).")

    # Decode with Pillow — this is the real content-type check.
    try:
        img = Image.open(file_storage.stream)
        img.load()
    except (UnidentifiedImageError, OSError):
        raise UploadError("That file is not a valid JPEG, PNG or WEBP image.")

    fmt = (img.format or "").upper()
    if fmt not in _FORMAT_EXT:
        raise UploadError("Only JPEG, PNG and WEBP images are allowed.")
    ext = _FORMAT_EXT[fmt]

    # Apply EXIF orientation, then crop/resize for the target use.
    img = ImageOps.exif_transpose(img)
    if kind == "avatar":
        img = ImageOps.fit(img, AVATAR_SIZE, method=Image.LANCZOS)
    else:  # backdrop
        img.thumbnail(BACKDROP_MAX, Image.LANCZOS)

    # JPEG can't hold alpha; flatten transparency onto a dark background.
    if fmt == "JPEG" and img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGB")

    upload_dir = current_app.config["UPLOAD_DIR"]
    os.makedirs(upload_dir, exist_ok=True)
    name = f"{uuid.uuid4().hex}.{ext}"
    img.save(os.path.join(upload_dir, name))

    return f"/uploads/{name}"


def delete_upload(url: Optional[str]) -> None:
    """Best-effort removal of a previously stored upload (ignore failures)."""
    if not url or not url.startswith("/uploads/"):
        return
    name = os.path.basename(url)  # strips any path components defensively
    try:
        os.remove(os.path.join(current_app.config["UPLOAD_DIR"], name))
    except OSError:
        pass
