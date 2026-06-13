"""Server-side TMDB client + local caching.

The TMDB API key is read from config and *never* leaves the server. Every
public function degrades gracefully: on timeout / 429 / network error we return
empty results (or fall back to a cached Film) rather than bubbling a 500.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

import requests
from flask import current_app

from .extensions import db
from .models import Film

log = logging.getLogger(__name__)


class TMDBError(Exception):
    """Raised for a genuine 'not found' so callers can return a clean 404."""


def _get(path: str, **params) -> Optional[dict]:
    """Low-level GET against TMDB. Returns parsed JSON or None on failure.

    We use a v3 API key passed as the `api_key` query param (the simplest of
    TMDB's auth schemes). Short timeout keeps a slow upstream from hanging us.
    """
    cfg = current_app.config
    params["api_key"] = cfg["TMDB_API_KEY"]
    url = f"{cfg['TMDB_API_BASE']}{path}"
    try:
        resp = requests.get(url, params=params, timeout=cfg["TMDB_TIMEOUT"])
    except requests.RequestException as exc:
        log.warning("TMDB request failed for %s: %s", path, exc)
        return None

    if resp.status_code == 404:
        raise TMDBError(f"TMDB resource not found: {path}")
    if resp.status_code == 429:
        log.warning("TMDB rate limited (429) for %s", path)
        return None
    if not resp.ok:
        log.warning("TMDB returned %s for %s", resp.status_code, path)
        return None
    try:
        return resp.json()
    except ValueError:
        return None


def _year_from(date_str: Optional[str]) -> Optional[int]:
    if date_str and len(date_str) >= 4 and date_str[:4].isdigit():
        return int(date_str[:4])
    return None


# --- search -------------------------------------------------------------------
def search_movies(query: str, page: int = 1) -> dict:
    """Return {results: [...], page, total_pages}. Empty on blank query/failure."""
    query = (query or "").strip()
    if not query:
        return {"results": [], "page": 1, "total_pages": 0}

    data = _get(
        "/search/movie", query=query, page=page, include_adult="false"
    )
    if not data:
        return {"results": [], "page": page, "total_pages": 0}

    results = [
        {
            "tmdb_id": m["id"],
            "title": m.get("title") or m.get("original_title") or "Untitled",
            "release_year": _year_from(m.get("release_date")),
            "poster_path": m.get("poster_path"),
            "overview": m.get("overview"),
        }
        for m in data.get("results", [])
    ]
    return {
        "results": results,
        "page": data.get("page", page),
        "total_pages": data.get("total_pages", 1),
    }


# --- trending (homepage) ------------------------------------------------------
def trending_movies() -> list[dict]:
    data = _get("/trending/movie/week")
    if not data:
        # fall back to popular, then to whatever we have cached locally.
        data = _get("/movie/popular")
    if not data:
        cached = Film.query.order_by(Film.cached_at.desc()).limit(18).all()
        return [_film_to_dict(f) for f in cached]

    out = []
    for m in data.get("results", [])[:18]:
        out.append(
            {
                "tmdb_id": m["id"],
                "title": m.get("title") or "Untitled",
                "release_year": _year_from(m.get("release_date")),
                "poster_path": m.get("poster_path"),
            }
        )
    return out


def _film_to_dict(f: Film) -> dict:
    return {
        "tmdb_id": f.tmdb_id,
        "title": f.title,
        "release_year": f.release_year,
        "poster_path": f.poster_path,
    }


# --- details + caching --------------------------------------------------------
def get_film(tmdb_id: int, force_refresh: bool = False) -> Optional[Film]:
    """Return a cached Film, fetching/refreshing from TMDB as needed.

    - If cached and fresh -> return as is.
    - If missing or stale -> fetch from TMDB and upsert.
    - If TMDB is unavailable but we have a (possibly stale) cache -> serve it.
    - If TMDB 404s and nothing is cached -> raise TMDBError for a clean 404.
    """
    film = db.session.get(Film, tmdb_id)
    if film and not film.is_stale and not force_refresh:
        return film

    try:
        data = _get(f"/movie/{tmdb_id}", append_to_response="credits,images")
    except TMDBError:
        # Bad id: if we somehow have it cached, serve that; else propagate 404.
        if film:
            return film
        raise

    if not data:
        # Network/rate-limit issue: serve stale cache if we have any.
        return film

    return _upsert_film(tmdb_id, data)


def _extract_director(credits: dict) -> Optional[str]:
    for member in credits.get("crew", []):
        if member.get("job") == "Director":
            return member.get("name")
    return None


def _upsert_film(tmdb_id: int, data: dict) -> Film:
    film = db.session.get(Film, tmdb_id)
    if film is None:
        film = Film(tmdb_id=tmdb_id)
        db.session.add(film)

    credits = data.get("credits", {}) or {}
    film.title = data.get("title") or data.get("original_title") or "Untitled"
    film.release_year = _year_from(data.get("release_date"))
    film.poster_path = data.get("poster_path")
    film.backdrop_path = data.get("backdrop_path")
    film.overview = data.get("overview")
    film.runtime = data.get("runtime")
    film.tmdb_rating = data.get("vote_average")
    film.director = _extract_director(credits)
    film.cached_at = datetime.utcnow()
    db.session.commit()
    return film


def get_film_credits(tmdb_id: int, limit: int = 12) -> list[dict]:
    """Top-billed cast for the film page. Returns [] on any failure."""
    try:
        data = _get(f"/movie/{tmdb_id}", append_to_response="credits")
    except TMDBError:
        return []
    if not data:
        return []
    cfg = current_app.config
    cast = []
    for person in (data.get("credits", {}) or {}).get("cast", [])[:limit]:
        profile = person.get("profile_path")
        cast.append(
            {
                "name": person.get("name"),
                "character": person.get("character"),
                "profile_url": (
                    f"{cfg['TMDB_IMAGE_BASE']}/w185{profile}" if profile else None
                ),
            }
        )
    return cast


def ensure_film_cached(tmdb_id: int) -> Optional[Film]:
    """Used before creating a log/watchlist row for a not-yet-cached film."""
    return get_film(tmdb_id)
