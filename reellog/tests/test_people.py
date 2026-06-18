"""Tests for the /person/<id> route (TMDB mocked at the _get boundary)."""
from __future__ import annotations

from unittest import mock

import pytest

from app.extensions import db
from app.models import Film, LogEntry, Person

PERSON_PAYLOAD = {
    "id": 5081,
    "name": "Emily Blunt",
    "profile_path": "/profile.jpg",
    "biography": "An English actress known for many films.",
    "known_for_department": "Acting",
    "movie_credits": {
        "cast": [
            {
                "id": 447332,
                "title": "A Quiet Place",
                "release_date": "2018-04-03",
                "poster_path": "/quiet.jpg",
                "popularity": 80.0,
                "character": "Evelyn Abbott",
            },
            {
                "id": 273481,
                "title": "Sicario",
                "release_date": "2015-09-18",
                "poster_path": "/sicario.jpg",
                "popularity": 40.0,
                "character": "Kate Macer",
            },
        ],
        "crew": [],
    },
}


def test_person_page_renders_with_filmography(client):
    with mock.patch("app.tmdb._get", return_value=PERSON_PAYLOAD):
        resp = client.get("/person/5081")
    assert resp.status_code == 200
    assert b"Emily Blunt" in resp.data
    assert b"Films starring" in resp.data
    # Both films appear, sorted by popularity (A Quiet Place first).
    body = resp.data.decode()
    assert "/film/447332" in body
    assert "/film/273481" in body
    assert body.index("/film/447332") < body.index("/film/273481")


def test_person_caches_identity(app, client):
    with mock.patch("app.tmdb._get", return_value=PERSON_PAYLOAD):
        client.get("/person/5081")
    cached = db.session.get(Person, 5081)
    assert cached is not None
    assert cached.name == "Emily Blunt"
    assert cached.known_for_department == "Acting"


def test_person_unknown_id_is_404(client):
    from app.tmdb import TMDBError

    with mock.patch("app.tmdb._get", side_effect=TMDBError("not found")):
        resp = client.get("/person/999999")
    assert resp.status_code == 404


def test_person_tmdb_outage_without_cache_is_404(client):
    # _get returns None on network/rate-limit failure; nothing cached -> 404.
    with mock.patch("app.tmdb._get", return_value=None):
        resp = client.get("/person/12345")
    assert resp.status_code == 404


def test_person_watched_stat_for_logged_in_user(auth_client, user):
    # Seed a cached film + a log so the intersection is non-empty.
    db.session.add(Film(tmdb_id=447332, title="A Quiet Place", release_year=2018))
    db.session.add(LogEntry(user_id=user.id, film_id=447332))
    db.session.commit()

    with mock.patch("app.tmdb._get", return_value=PERSON_PAYLOAD):
        resp = auth_client.get("/person/5081")
    assert resp.status_code == 200
    # Watched 1 of 2 (50%).
    assert b"watched" in resp.data.lower()
    assert b"50%" in resp.data
