"""Konfiguration: env-Datei, Datenbank, TMDB, Cookies und Limits."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

INSTANCE_DIR = PROJECT_ROOT / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)


def _require(name: str) -> str:
    # SECRET_KEY und TMDB_API_KEY muessen gesetzt sein, sonst startet die App nicht.
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(
            f"Missing required environment variable {name!r}. "
            f"Copy .env.example to .env and fill it in."
        )
    return value


class Config:
    # Alles, was Flask oder eigene Helper spaeter aus current_app.config lesen.
    SECRET_KEY = _require("SECRET_KEY")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URI", f"sqlite:///{INSTANCE_DIR / 'app.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    TMDB_API_KEY = _require("TMDB_API_KEY")
    TMDB_API_BASE = "https://api.themoviedb.org/3"
    TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p"
    TMDB_TIMEOUT = 6
    TMDB_CACHE_DAYS = 7

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"

    TAILWIND_CDN = os.environ.get("TAILWIND_CDN", "0") == "1"

    REVIEW_MAX_LEN = 5000
    BIO_MAX_LEN = 500
    URL_MAX_LEN = 500

    UPLOAD_DIR = INSTANCE_DIR / "uploads"
    UPLOAD_MAX_BYTES = 5 * 1024 * 1024
