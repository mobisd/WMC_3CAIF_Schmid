"""Tests for the redesigned profile, the Films tab, and profile actions."""
from __future__ import annotations

from app.extensions import db
from app.models import FavoriteFilm, Film, LogEntry, User, WatchlistItem


def _seed_activity(user):
    f1 = Film(tmdb_id=101, title="First", release_year=2001, backdrop_path="/b1.jpg")
    f2 = Film(tmdb_id=102, title="Second", release_year=2002)
    db.session.add_all([f1, f2])
    db.session.add(LogEntry(user_id=user.id, film_id=101, rating=8, liked=True, review="Great film."))
    db.session.add(LogEntry(user_id=user.id, film_id=102, rating=6))
    db.session.add(WatchlistItem(user_id=user.id, film_id=102))
    db.session.add(FavoriteFilm(user_id=user.id, film_id=101, position=0))
    db.session.commit()


def test_profile_shows_sections_and_edit_button(auth_client, user):
    _seed_activity(user)
    resp = auth_client.get(f"/{user.username}")
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "Favourite films" in body
    assert "Recent activity" in body
    assert "Recent reviews" in body
    assert "Great film." in body
    # Own profile shows the Edit button + loads the own-profile JS.
    assert "Edit profile" in body
    assert "/settings" in body
    assert "js/profile.js" in body


def test_other_profile_hides_edit_button(client, user):
    # A second user viewing alice's profile must not see "Edit profile".
    bob = User(username="bob", email="bob@example.com")
    bob.set_password("password123")
    db.session.add(bob)
    db.session.commit()
    client.post("/login", data={"identifier": "bob", "password": "password123"})

    resp = client.get(f"/{user.username}")
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "Edit profile" not in body
    # The own-profile editing JS must not load on someone else's profile.
    assert "js/profile.js" not in body


def test_films_tab_lists_distinct_films(auth_client, user):
    _seed_activity(user)
    # Log "First" twice — it should still appear once on the Films tab.
    db.session.add(LogEntry(user_id=user.id, film_id=101, rating=10))
    db.session.commit()
    resp = auth_client.get(f"/{user.username}/films")
    assert resp.status_code == 200
    body = resp.data.decode()
    assert body.count("/film/101") == 1


def test_settings_page_renders(auth_client):
    resp = auth_client.get("/settings")
    assert resp.status_code == 200
    assert b"multipart/form-data" in resp.data
    assert b"avatar_file" in resp.data


def test_set_profile_backdrop(auth_client, user):
    db.session.add(Film(tmdb_id=200, title="Backdroppy", backdrop_path="/bd.jpg"))
    db.session.commit()
    resp = auth_client.post("/api/profile/backdrop", json={"tmdb_id": 200})
    assert resp.status_code == 200
    assert resp.get_json()["backdrop_url"].endswith("/bd.jpg")
    assert db.session.get(User, user.id).backdrop_url is not None


def test_set_profile_backdrop_no_image_is_422(auth_client):
    db.session.add(Film(tmdb_id=201, title="No backdrop", backdrop_path=None))
    db.session.commit()
    resp = auth_client.post("/api/profile/backdrop", json={"tmdb_id": 201})
    assert resp.status_code == 422
