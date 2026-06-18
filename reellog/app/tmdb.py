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
from .models import Film, Person

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


def get_film_people(tmdb_id: int, cast_limit: int = 12) -> dict:
    """Top-billed cast + the director's id for the film page.

    Returns ``{"cast": [...], "director_id": int|None}``. Each cast entry
    includes the person's TMDB ``id`` so the template can link to the person
    page. Degrades to ``{"cast": [], "director_id": None}`` on any failure.
    """
    empty = {"cast": [], "director_id": None}
    try:
        data = _get(f"/movie/{tmdb_id}", append_to_response="credits")
    except TMDBError:
        return empty
    if not data:
        return empty

    cfg = current_app.config
    credits = data.get("credits", {}) or {}
    cast = []
    for person in credits.get("cast", [])[:cast_limit]:
        profile = person.get("profile_path")
        cast.append(
            {
                "id": person.get("id"),
                "name": person.get("name"),
                "character": person.get("character"),
                "profile_url": (
                    f"{cfg['TMDB_IMAGE_BASE']}/w185{profile}" if profile else None
                ),
            }
        )

    director_id = None
    for member in credits.get("crew", []):
        if member.get("job") == "Director":
            director_id = member.get("id")
            break

    return {"cast": cast, "director_id": director_id}


def get_person(tmdb_id: int, force_refresh: bool = False):
    """Return ``(Person, filmography)`` for the person page.

    - Caches the person's identity/bio locally (mirrors get_film) so the page
      survives TMDB outages.
    - ``filmography`` is a list of film dicts (tmdb_id, title, release_year,
      poster_path, character/job, popularity), de-duped and sorted by
      popularity desc. It is built from the live response and is ``[]`` when
      TMDB is unavailable.
    - Raises TMDBError for an unknown id with nothing cached (clean 404).
    """
    person = db.session.get(Person, tmdb_id)
    if person and not person.is_stale and not force_refresh:
        # Fresh identity cached, but we still want a current filmography.
        filmography = _fetch_filmography(tmdb_id)
        return person, filmography

    try:
        data = _get(f"/person/{tmdb_id}", append_to_response="movie_credits")
    except TMDBError:
        if person:
            return person, _fetch_filmography(tmdb_id)
        raise

    if not data:
        # Network/rate-limit issue: serve stale cache if we have any.
        if person:
            return person, []
        return None, []

    person = _upsert_person(tmdb_id, data)
    filmography = _filmography_from_credits(data.get("movie_credits", {}) or {})
    return person, filmography


def _upsert_person(tmdb_id: int, data: dict) -> Person:
    person = db.session.get(Person, tmdb_id)
    if person is None:
        person = Person(tmdb_id=tmdb_id)
        db.session.add(person)
    person.name = data.get("name") or "Unknown"
    person.profile_path = data.get("profile_path")
    person.biography = data.get("biography")
    person.known_for_department = data.get("known_for_department")
    person.cached_at = datetime.utcnow()
    db.session.commit()
    return person


def _fetch_filmography(tmdb_id: int) -> list[dict]:
    """Fetch just the movie_credits for an already-cached person."""
    try:
        data = _get(f"/person/{tmdb_id}", append_to_response="movie_credits")
    except TMDBError:
        return []
    if not data:
        return []
    return _filmography_from_credits(data.get("movie_credits", {}) or {})


def _filmography_from_credits(movie_credits: dict) -> list[dict]:
    """Merge acting + directing credits into a de-duped, popularity-sorted list.

    A film the person both acted in and directed appears once; we keep the
    directing role label when present (it's the more notable credit).
    """
    by_id: dict[int, dict] = {}

    def add(entry: dict, role: str):
        mid = entry.get("id")
        if not mid:
            return
        existing = by_id.get(mid)
        film = {
            "tmdb_id": mid,
            "title": entry.get("title") or entry.get("original_title") or "Untitled",
            "release_year": _year_from(entry.get("release_date")),
            "poster_path": entry.get("poster_path"),
            "popularity": entry.get("popularity") or 0,
            "role": role,
        }
        # Prefer the directing label if we see the film twice.
        if existing is None or role == "Director":
            by_id[mid] = film

    for entry in movie_credits.get("cast", []):
        add(entry, entry.get("character") or "")
    for entry in movie_credits.get("crew", []):
        if entry.get("job") == "Director":
            add(entry, "Director")

    films = list(by_id.values())
    films.sort(key=lambda f: f["popularity"], reverse=True)
    return films


def ensure_film_cached(tmdb_id: int) -> Optional[Film]:
    """Used before creating a log/watchlist row for a not-yet-cached film."""
    return get_film(tmdb_id)
