"""TMDB client and local caching."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

import requests
from flask import current_app

from .extensions import db
from .models import Film

log = logging.getLogger(__name__)
_IMAGE_CACHE: dict[int, tuple[datetime, dict]] = {}
IMAGE_CACHE_TTL = timedelta(minutes=15)


class TMDBError(Exception):
    """Raised when TMDB reports a missing resource."""


def _get(path: str, **params) -> Optional[dict]:
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


def search_movies(query: str, page: int = 1) -> dict:
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


def trending_movies() -> list[dict]:
    data = _get("/trending/movie/week")
    if not data:
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


def get_film(tmdb_id: int, force_refresh: bool = False) -> Optional[Film]:
    film = db.session.get(Film, tmdb_id)
    if film and not film.is_stale and not force_refresh:
        return film

    try:
        data = _get(f"/movie/{tmdb_id}", append_to_response="credits,images")
    except TMDBError:
        if film:
            return film
        raise

    if not data:
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
                "id": person.get("id"),
                "name": person.get("name"),
                "character": person.get("character"),
                "profile_url": (
                    f"{cfg['TMDB_IMAGE_BASE']}/w185{profile}" if profile else None
                ),
            }
        )
    return cast


def get_person(person_id: int) -> Optional[dict]:
    try:
        data = _get(f"/person/{person_id}")
    except TMDBError:
        raise
    if not data:
        return None

    cfg = current_app.config
    profile = data.get("profile_path")
    return {
        "id": data.get("id", person_id),
        "name": data.get("name") or "Unknown actor",
        "biography": data.get("biography"),
        "birthday": data.get("birthday"),
        "deathday": data.get("deathday"),
        "place_of_birth": data.get("place_of_birth"),
        "known_for_department": data.get("known_for_department"),
        "profile_url": f"{cfg['TMDB_IMAGE_BASE']}/h632{profile}" if profile else None,
        "tmdb_url": f"https://www.themoviedb.org/person/{person_id}",
    }


def get_person_movie_credits(person_id: int, limit: int = 40) -> list[dict]:
    try:
        data = _get(f"/person/{person_id}/movie_credits")
    except TMDBError:
        return []
    if not data:
        return []

    credits = []
    for movie in data.get("cast", []):
        tmdb_id = movie.get("id")
        title = movie.get("title") or movie.get("original_title")
        if not tmdb_id or not title:
            continue
        credits.append(
            {
                "tmdb_id": tmdb_id,
                "title": title,
                "release_year": _year_from(movie.get("release_date")),
                "poster_path": movie.get("poster_path"),
                "character": movie.get("character"),
                "popularity": movie.get("popularity") or 0,
            }
        )
    credits.sort(key=lambda item: item["popularity"], reverse=True)
    return credits[:limit]


def ensure_film_cached(tmdb_id: int) -> Optional[Film]:
    return get_film(tmdb_id)


def get_movie_images(tmdb_id: int, limit: int = 30) -> dict:
    cached = _IMAGE_CACHE.get(tmdb_id)
    now = datetime.utcnow()
    if cached and now - cached[0] < IMAGE_CACHE_TTL:
        return cached[1]

    try:
        data = _get(
            f"/movie/{tmdb_id}/images",
            include_image_language="en,null",
        )
    except TMDBError:
        return {"posters": [], "backdrops": []}
    if not data:
        return {"posters": [], "backdrops": []}

    def clean(items: list[dict]) -> list[dict]:
        out = []
        for item in items[:limit]:
            path = item.get("file_path")
            if not path:
                continue
            out.append(
                {
                    "file_path": path,
                    "width": item.get("width"),
                    "height": item.get("height"),
                    "language": item.get("iso_639_1"),
                    "vote_average": item.get("vote_average"),
                }
            )
        return out

    result = {
        "posters": clean(data.get("posters", [])),
        "backdrops": clean(data.get("backdrops", [])),
    }
    _IMAGE_CACHE[tmdb_id] = (now, result)
    return result
