"""Film image helpers."""
from __future__ import annotations

from flask import current_app, url_for

from .models import Film, User, UserFilmImage


def _image_url(path: str | None, size: str, fallback: str) -> str:
    if path:
        return f"{current_app.config['TMDB_IMAGE_BASE']}/{size}{path}"
    return url_for("static", filename=fallback)


def image_override_for(user: User | None, film_id: int) -> UserFilmImage | None:
    if not user or not getattr(user, "is_authenticated", False):
        return None
    return UserFilmImage.query.filter_by(user_id=user.id, film_id=film_id).first()


def effective_image_paths(film: Film, user: User | None = None) -> dict:
    override = image_override_for(user, film.tmdb_id)
    return {
        "poster_path": override.poster_path if override and override.poster_path else film.poster_path,
        "backdrop_path": override.backdrop_path if override and override.backdrop_path else film.backdrop_path,
        "has_poster_override": bool(override and override.poster_path),
        "has_backdrop_override": bool(override and override.backdrop_path),
    }


def effective_poster_url(film: Film, user: User | None = None, size: str = "w342") -> str:
    paths = effective_image_paths(film, user)
    return _image_url(paths["poster_path"], size, "img/poster-fallback.svg")


def effective_backdrop_url(film: Film, user: User | None = None, size: str = "w1280") -> str:
    paths = effective_image_paths(film, user)
    return _image_url(paths["backdrop_path"], size, "img/backdrop-fallback.svg")
