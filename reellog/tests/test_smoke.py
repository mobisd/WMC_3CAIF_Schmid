"""Smoke tests: every key page renders without a template/route error."""
from __future__ import annotations

from unittest import mock


def test_index_renders(client):
    with mock.patch("app.films.routes.trending_movies", return_value=[]):
        resp = client.get("/")
    assert resp.status_code == 200


def test_film_page_renders(client, film):
    with mock.patch(
        "app.films.routes.get_film_people",
        return_value={"cast": [], "director_id": None},
    ):
        resp = client.get(f"/film/{film.tmdb_id}")
    assert resp.status_code == 200
    assert b"Inception" in resp.data


def test_profile_renders(client, user):
    resp = client.get(f"/{user.username}")
    assert resp.status_code == 200
    assert b"Alice" in resp.data


def test_login_register_render(client):
    assert client.get("/login").status_code == 200
    assert client.get("/register").status_code == 200
