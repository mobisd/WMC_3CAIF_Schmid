"""Application configuration, loaded from environment variables.

We deliberately fail fast (raise RuntimeError) when required secrets are
missing so the app never boots in an insecure / broken half-configured state.
Secrets (SECRET_KEY, TMDB_API_KEY) must come from the environment / .env and
are *never* exposed to the client.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root (one level above the app package).
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# instance/ holds the SQLite file; keep it out of version control.
INSTANCE_DIR = PROJECT_ROOT / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)


def _require(name: str) -> str:
    """Return an env var or raise a clear error if it is missing/empty."""
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(
            f"Missing required environment variable {name!r}. "
            f"Copy .env.example to .env and fill it in."
        )
    return value


class Config:
    # --- Security ---------------------------------------------------------
    SECRET_KEY = _require("SECRET_KEY")

    # --- Database ---------------------------------------------------------
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URI", f"sqlite:///{INSTANCE_DIR / 'app.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- TMDB -------------------------------------------------------------
    TMDB_API_KEY = _require("TMDB_API_KEY")
    TMDB_API_BASE = "https://api.themoviedb.org/3"
    TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p"
    TMDB_TIMEOUT = 6  # seconds; keep short so a slow TMDB never hangs a request
    TMDB_CACHE_DAYS = 7  # refresh a cached Film if older than this

    # --- Session cookie hardening ----------------------------------------
    # HttpOnly + SameSite=Lax are safe defaults for local/dev.
    # SESSION_COOKIE_SECURE is left configurable: it MUST be True behind HTTPS
    # in production (see README), but True would break plain-HTTP localhost.
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"

    # When True, base.html uses the Tailwind Play CDN (dev convenience only).
    # Default is False because we ship a pre-built static/css/output.css, so a
    # fresh clone is styled with zero tooling. Set TAILWIND_CDN=1 if you'd
    # rather iterate on classes against the CDN without rebuilding.
    TAILWIND_CDN = os.environ.get("TAILWIND_CDN", "0") == "1"

    # Validation limits, kept here so routes and templates agree.
    REVIEW_MAX_LEN = 5000
    BIO_MAX_LEN = 500
    URL_MAX_LEN = 500
