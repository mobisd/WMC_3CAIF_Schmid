"""JSON API blueprint.

All mutating endpoints require login and are CSRF-protected (the client sends
the token via the X-CSRFToken header — see static/js/api.js). Every edit/delete
enforces ownership: a user may only touch their own logs. We return precise
status codes: 401 (not logged in), 403 (not owner), 404 (missing), 422
(validation), 409 (conflict), 200/201 (ok).
"""
from __future__ import annotations

from datetime import date

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from ..config import Config
from ..extensions import db
from ..models import FavoriteFilm, LogEntry, WatchlistItem
from ..tmdb import TMDBError, ensure_film_cached, search_movies
from ..validators import parse_rating, parse_watched_on

api_bp = Blueprint("api", __name__)


def _err(message: str, status: int):
    return jsonify({"ok": False, "error": message}), status


@api_bp.route("/search")
def api_search():
    """Live-search endpoint for the nav dropdown (debounced client-side)."""
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"results": []})
    data = search_movies(query, page=1)
    # Trim to the fields the dropdown needs; titles are escaped client-side.
    results = [
        {
            "tmdb_id": r["tmdb_id"],
            "title": r["title"],
            "year": r["release_year"],
            "poster_path": r["poster_path"],
        }
        for r in data["results"][:8]
    ]
    return jsonify({"results": results})


@api_bp.route("/watchlist/toggle", methods=["POST"])
@login_required
def watchlist_toggle():
    payload = request.get_json(silent=True) or {}
    tmdb_id = payload.get("tmdb_id")
    if not isinstance(tmdb_id, int):
        return _err("tmdb_id (integer) is required.", 422)

    # Make sure the film exists locally so the FK is valid.
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


@api_bp.route("/favorites/toggle", methods=["POST"])
@login_required
def favorites_toggle():
    """Add/remove a film from the user's 'favourite four'.

    Enforces the cap (Config.MAX_FAVORITE_FILMS): adding a 5th returns 409.
    """
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

    existing = FavoriteFilm.query.filter_by(
        user_id=current_user.id, film_id=tmdb_id
    ).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        count = FavoriteFilm.query.filter_by(user_id=current_user.id).count()
        return jsonify({"ok": True, "is_favorite": False, "count": count})

    count = FavoriteFilm.query.filter_by(user_id=current_user.id).count()
    if count >= Config.MAX_FAVORITE_FILMS:
        return _err(
            f"You can only pin {Config.MAX_FAVORITE_FILMS} favourite films.", 409
        )

    db.session.add(
        FavoriteFilm(user_id=current_user.id, film_id=tmdb_id, position=count)
    )
    db.session.commit()
    return jsonify({"ok": True, "is_favorite": True, "count": count + 1})


@api_bp.route("/profile/backdrop", methods=["POST"])
@login_required
def set_profile_backdrop():
    """Set the user's profile backdrop to a film's backdrop image."""
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
    if not film.backdrop_path:
        return _err("That film has no backdrop image.", 422)

    current_user.backdrop_url = film.backdrop_url("w1280")
    db.session.commit()
    return jsonify({"ok": True, "backdrop_url": current_user.backdrop_url})


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
    """Validate and normalise the shared log fields. Raises ValueError."""
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
            fields["review"] = review or None  # store empty review as NULL

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
