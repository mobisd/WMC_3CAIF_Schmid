"""JSON API blueprint."""
from __future__ import annotations

from datetime import date

from flask import current_app
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import or_

from ..config import Config
from ..extensions import db
from ..models import LogEntry, User, UserFilmImage, WatchlistItem
from ..tmdb import TMDBError, ensure_film_cached, get_movie_images, search_movies
from ..validators import parse_rating, parse_watched_on

api_bp = Blueprint("api", __name__)


def _err(message: str, status: int):
    return jsonify({"ok": False, "error": message}), status


def _tmdb_image_url(path: str, size: str = "w1280") -> str:
    return f"{current_app.config['TMDB_IMAGE_BASE']}/{size}{path}"


@api_bp.route("/search")
def api_search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"results": []})
    data = search_movies(query, page=1)
    results = [
        {
            "tmdb_id": r["tmdb_id"],
            "title": r["title"],
            "year": r["release_year"],
            "poster_path": r["poster_path"],
        }
        for r in data["results"][:8]
    ]
    users = [
        {
            "username": u.username,
            "name": u.name,
            "avatar_url": u.avatar_url,
        }
        for u in (
            User.query.filter(
                or_(
                    User.username.ilike(f"%{query}%"),
                    User.display_name.ilike(f"%{query}%"),
                )
            )
            .order_by(User.username.asc())
            .limit(5)
            .all()
        )
    ]
    return jsonify({"results": results, "users": users})


@api_bp.route("/watchlist/toggle", methods=["POST"])
@login_required
def watchlist_toggle():
    payload = request.get_json(silent=True) or {}
    tmdb_id = payload.get("tmdb_id")
    if not isinstance(tmdb_id, int):
        return _err("tmdb_id (integer) is required.", 422)

    try:
        film = ensure_film_cached(tmdb_id)
    except TMDBError:
        return _err("Film not found.", 404)
    if film is None:
        return _err("Film data is temporarily unavailable.", 503)

    existing = WatchlistItem.query.filter_by(
        user_id=current_user.id, film_id=tmdb_id
    ).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({"ok": True, "in_watchlist": False})

    db.session.add(WatchlistItem(user_id=current_user.id, film_id=tmdb_id))
    db.session.commit()
    return jsonify({"ok": True, "in_watchlist": True})


@api_bp.route("/movies/<int:tmdb_id>/images")
@login_required
def movie_images(tmdb_id: int):
    try:
        film = ensure_film_cached(tmdb_id)
    except TMDBError:
        return _err("Film not found.", 404)
    if film is None:
        return _err("Film data is temporarily unavailable.", 503)

    images = get_movie_images(tmdb_id)
    override = UserFilmImage.query.filter_by(
        user_id=current_user.id, film_id=tmdb_id
    ).first()
    return jsonify(
        {
            "ok": True,
            "tmdb_id": tmdb_id,
            "default_poster_path": film.poster_path,
            "default_backdrop_path": film.backdrop_path,
            "poster_path": override.poster_path if override else None,
            "backdrop_path": override.backdrop_path if override else None,
            "posters": images["posters"],
            "backdrops": images["backdrops"],
        }
    )


@api_bp.route("/profile/backdrop", methods=["POST", "DELETE"])
@login_required
def profile_backdrop():
    if request.method == "DELETE":
        current_user.backdrop_url = None
        db.session.commit()
        return jsonify({"ok": True, "backdrop_url": None})

    payload = request.get_json(silent=True) or {}
    path = payload.get("backdrop_path")
    tmdb_id = payload.get("tmdb_id")
    if not isinstance(path, str) or not path.startswith("/"):
        return _err("backdrop_path is required.", 422)
    if not isinstance(tmdb_id, int):
        return _err("tmdb_id (integer) is required.", 422)

    images = get_movie_images(tmdb_id)
    allowed = {item["file_path"] for item in images["backdrops"]}
    if path not in allowed:
        return _err("Choose a valid TMDB backdrop.", 422)

    current_user.backdrop_url = _tmdb_image_url(path, "original")
    db.session.commit()
    return jsonify({"ok": True, "backdrop_url": current_user.backdrop_url})


@api_bp.route("/film-images/<int:tmdb_id>", methods=["PATCH"])
@login_required
def update_film_images(tmdb_id: int):
    try:
        film = ensure_film_cached(tmdb_id)
    except TMDBError:
        return _err("Film not found.", 404)
    if film is None:
        return _err("Film data is temporarily unavailable.", 503)

    payload = request.get_json(silent=True) or {}
    field = payload.get("field")
    path = payload.get("path")
    if field not in {"poster", "backdrop"}:
        return _err("field must be poster or backdrop.", 422)
    if path is not None and (not isinstance(path, str) or not path.startswith("/")):
        return _err("Choose a valid TMDB image.", 422)

    images = get_movie_images(tmdb_id)
    allowed_key = "posters" if field == "poster" else "backdrops"
    if path is not None and path not in {item["file_path"] for item in images[allowed_key]}:
        return _err("Choose a valid TMDB image.", 422)

    override = UserFilmImage.query.filter_by(
        user_id=current_user.id, film_id=tmdb_id
    ).first()
    if override is None:
        override = UserFilmImage(user_id=current_user.id, film_id=tmdb_id)
        db.session.add(override)

    if field == "poster":
        override.poster_path = path
    else:
        override.backdrop_path = path
        if payload.get("use_as_profile_backdrop") and path:
            current_user.backdrop_url = _tmdb_image_url(path, "original")

    if override.poster_path is None and override.backdrop_path is None:
        db.session.delete(override)

    db.session.commit()
    return jsonify({"ok": True})


def _serialize_log(log: LogEntry) -> dict:
    return {
        "id": log.id,
        "tmdb_id": log.film_id,
        "watched_on": log.watched_on.isoformat() if log.watched_on else None,
        "rating": log.rating,
        "stars": log.stars,
        "review": log.review,
        "liked": log.liked,
        "is_rewatch": log.is_rewatch,
        "contains_spoilers": log.contains_spoilers,
    }


def _read_log_fields(payload: dict, *, partial: bool = False) -> dict:
    fields = {}

    if not partial or "rating" in payload:
        fields["rating"] = parse_rating(payload.get("rating"))
    if not partial or "watched_on" in payload:
        fields["watched_on"] = parse_watched_on(payload.get("watched_on"))

    if not partial or "review" in payload:
        review = payload.get("review")
        if review is None:
            fields["review"] = None
        else:
            review = str(review).strip()
            if len(review) > Config.REVIEW_MAX_LEN:
                raise ValueError(
                    f"Review is too long (max {Config.REVIEW_MAX_LEN} characters)."
                )
            fields["review"] = review or None

    for key in ("liked", "is_rewatch", "contains_spoilers"):
        if not partial or key in payload:
            fields[key] = bool(payload.get(key, False))
    return fields


def _current_log(user_id: int, film_id: int) -> LogEntry | None:
    return (
        LogEntry.query.filter_by(user_id=user_id, film_id=film_id)
        .order_by(LogEntry.created_at.desc(), LogEntry.id.desc())
        .first()
    )


@api_bp.route("/logs", methods=["POST"])
@login_required
def create_log():
    payload = request.get_json(silent=True) or {}
    tmdb_id = payload.get("tmdb_id")
    if not isinstance(tmdb_id, int):
        return _err("tmdb_id (integer) is required.", 422)

    try:
        film = ensure_film_cached(tmdb_id)
    except TMDBError:
        return _err("Film not found.", 404)
    if film is None:
        return _err("Film data is temporarily unavailable.", 503)

    try:
        fields = _read_log_fields(payload, partial=True)
    except ValueError as exc:
        return _err(str(exc), 422)

    is_rewatch = bool(payload.get("is_rewatch", False))
    log = None if is_rewatch else _current_log(current_user.id, tmdb_id)
    created = log is None
    if log is None:
        fields.setdefault("watched_on", date.today())
        fields.setdefault("rating", None)
        fields.setdefault("review", None)
        fields.setdefault("liked", False)
        fields.setdefault("contains_spoilers", False)
        fields["is_rewatch"] = is_rewatch
        log = LogEntry(user_id=current_user.id, film_id=tmdb_id, **fields)
        db.session.add(log)
    else:
        fields.pop("is_rewatch", None)
        for key, value in fields.items():
            setattr(log, key, value)

    db.session.commit()
    return jsonify({"ok": True, "log": _serialize_log(log)}), 201 if created else 200


@api_bp.route("/logs/<int:log_id>", methods=["PATCH"])
@login_required
def update_log(log_id: int):
    log = db.session.get(LogEntry, log_id)
    if log is None:
        return _err("Log not found.", 404)
    if log.user_id != current_user.id:
        return _err("You can only edit your own logs.", 403)

    payload = request.get_json(silent=True) or {}
    try:
        fields = _read_log_fields(payload)
    except ValueError as exc:
        return _err(str(exc), 422)

    for key, value in fields.items():
        setattr(log, key, value)
    db.session.commit()
    return jsonify({"ok": True, "log": _serialize_log(log)})


@api_bp.route("/logs/<int:log_id>", methods=["DELETE"])
@login_required
def delete_log(log_id: int):
    log = db.session.get(LogEntry, log_id)
    if log is None:
        return _err("Log not found.", 404)
    if log.user_id != current_user.id:
        return _err("You can only delete your own logs.", 403)

    db.session.delete(log)
    db.session.commit()
    return jsonify({"ok": True})
