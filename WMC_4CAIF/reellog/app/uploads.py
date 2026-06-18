"""Upload-Helfer fuer Avatare: Groesse, Dateityp und Dateiname pruefen."""
from __future__ import annotations

import os
import uuid

from flask import current_app
from werkzeug.utils import secure_filename

ALLOWED_EXTS = {"jpg", "jpeg", "png", "webp", "gif"}


class UploadError(ValueError):
    pass


def save_avatar(file_storage) -> str:
    # Speichert nur erlaubte Bilddateien und gibt danach die /uploads/-URL zurueck.
    if file_storage is None or not file_storage.filename:
        raise UploadError("No file selected.")

    stream = file_storage.stream
    pos = stream.tell()
    stream.seek(0, os.SEEK_END)
    size = stream.tell()
    stream.seek(pos)
    if size > current_app.config["UPLOAD_MAX_BYTES"]:
        raise UploadError("Avatar image is too large.")

    original = secure_filename(file_storage.filename)
    ext = original.rsplit(".", 1)[-1].lower() if "." in original else ""
    if ext not in ALLOWED_EXTS:
        raise UploadError("Use a JPG, PNG, WEBP or GIF image.")

    upload_dir = current_app.config["UPLOAD_DIR"]
    os.makedirs(upload_dir, exist_ok=True)
    name = f"{uuid.uuid4().hex}.{ext}"
    file_storage.save(os.path.join(upload_dir, name))
    return f"/uploads/{name}"
