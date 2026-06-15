"""Films blueprint: home, server-rendered search, and the film detail page."""
from __future__ import annotations

from flask import Blueprint, abort, render_template, request
from flask_login import current_user
from sqlalchemy.orm import joinedload

from ..images import effective_backdrop_url, effective_image_paths, effective_poster_url
from ..extensions import db
from ..models import Film, LogEntry
from ..tmdb import (
    TMDBError,
    get_film,
    get_film_credits,
    search_movies,
    trending_movies,
)

films_bp = Blueprint("films", __name__)


@films_bp.route("/")
def index():
    trending = trending_movies()
    recent_logs = []
    if current_user.is_authenticated:
        for item in trending:
            cached = db.session.get(Film, item["tmdb_id"])
            if cached:
                item["poster_url"] = effective_poster_url(cached, current_user, "w500")
        recent_logs = (
            LogEntry.query.options(joinedload(LogEntry.film))
            .filter_by(user_id=current_user.id)
            .order_by(LogEntry.created_at.desc())
            .limit(8)
            .all()
        )
    return render_template(
        "index.html", trending=trending, recent_logs=recent_logs
    )


@films_bp.route("/search")
def search():
    query = request.args.get("q", "").strip()
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (TypeError, ValueError):
        page = 1

    results = {"results": [], "page": 1, "total_pages": 0}
    if query:
        results = search_movies(query, page=page)
        if current_user.is_authenticated:
            for item in results["results"]:
                cached = db.session.get(Film, item["tmdb_id"])
                if cached:
                    item["poster_url"] = effective_poster_url(cached, current_user, "w342")

    return render_template(
        "search.html",
        query=query,
        results=results["results"],
        page=results["page"],
        total_pages=results["total_pages"],
    )


@films_bp.route("/film/<int:tmdb_id>")
def film(tmdb_id: int):
    try:
        film_obj = get_film(tmdb_id)
    except TMDBError:
        abort(404)
    if film_obj is None:
        abort(404)

    cast = get_film_credits(tmdb_id)

    reviews = (
        LogEntry.query.options(joinedload(LogEntry.user))
        .filter(LogEntry.film_id == tmdb_id, LogEntry.review.isnot(None))
        .order_by(LogEntry.created_at.desc())
        .all()
    )
    reviews = [r for r in reviews if r.has_review]

    my_logs = []
    user_state = {
        "in_watchlist": False,
        "watched": False,
        "rating": None,
    }
    if current_user.is_authenticated:
        my_logs = (
            LogEntry.query.filter_by(user_id=current_user.id, film_id=tmdb_id)
            .order_by(LogEntry.created_at.desc())
            .all()
        )
        current_log = my_logs[0] if my_logs else None
        user_state = {
            "in_watchlist": current_user.in_watchlist(tmdb_id),
            "watched": current_log is not None,
            "rating": current_log.rating if current_log else None,
            "current_log": current_log,
        }
    else:
        user_state["current_log"] = None

    return render_template(
        "film.html",
        film=film_obj,
        effective_poster_url=effective_poster_url(film_obj, current_user, "w342"),
        effective_backdrop_url=effective_backdrop_url(film_obj, current_user, "w1280"),
        effective_paths=effective_image_paths(film_obj, current_user),
        cast=cast,
        reviews=reviews,
        my_logs=my_logs,
        user_state=user_state,
    )
