"""Small, dependency-free validation helpers shared across blueprints.

Keeping these in one place means the username rules / reserved names / URL
checks are defined once and can't drift between auth, settings and the API.
"""
from __future__ import annotations

import re
from datetime import date

USERNAME_RE = re.compile(r"^[a-z0-9_]{3,20}$")

# These collide with real routes, so they can never be usernames.
RESERVED_USERNAMES = {
    "settings",
    "api",
    "film",
    "search",
    "login",
    "register",
    "logout",
    "static",
    "admin",
}


def normalise_username(raw: str) -> str:
    return (raw or "").strip().lower()


def username_error(username: str) -> str | None:
    """Return an error message if invalid, else None."""
    if not USERNAME_RE.match(username):
        return "Username must be 3–20 chars: lowercase letters, numbers, underscores."
    if username in RESERVED_USERNAMES:
        return "That username is reserved. Please choose another."
    return None


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def email_error(email: str) -> str | None:
    if not email or not EMAIL_RE.match(email):
        return "Please enter a valid email address."
    if len(email) > 255:
        return "Email address is too long."
    return None


def password_error(password: str) -> str | None:
    if not password or len(password) < 8:
        return "Password must be at least 8 characters."
    if len(password) > 200:
        return "Password is too long."
    return None


def url_error(url: str, max_len: int = 500) -> str | None:
    """Validate an optional user-supplied image URL (avatar/backdrop)."""
    if not url:
        return None  # optional fields may be blank
    if len(url) > max_len:
        return "URL is too long."
    if not (url.startswith("http://") or url.startswith("https://")):
        return "URL must start with http:// or https://."
    return None


def parse_rating(value) -> int | None:
    """Accept an int 1..10 (half-star units) or None. Raises ValueError otherwise."""
    if value is None or value == "":
        return None
    try:
        rating = int(value)
    except (TypeError, ValueError):
        raise ValueError("Rating must be a whole number of half-stars (1–10).")
    if not 1 <= rating <= 10:
        raise ValueError("Rating must be between 1 and 10 (½–5 stars).")
    return rating


def parse_watched_on(value) -> date | None:
    """Parse an ISO date string; reject future dates. None/'' => None."""
    if not value:
        return None
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError("Date must be in YYYY-MM-DD format.")
    if parsed > date.today():
        raise ValueError("You can't log a film with a future date.")
    return parsed
