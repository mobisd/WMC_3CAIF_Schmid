from __future__ import annotations

import io
import re
import zipfile

from app.extensions import db
from app.images import effective_backdrop_url, effective_poster_url
from app.models import Film, LogEntry, User, UserFavoriteFilm, UserFilmImage, WatchlistItem


def _fake_images(_tmdb_id):
    return {
        "posters": [{"file_path": "/poster-a.jpg"}, {"file_path": "/poster-b.jpg"}],
        "backdrops": [{"file_path": "/back-a.jpg"}, {"file_path": "/back-b.jpg"}],
    }


def test_effective_image_helper_prefers_user_override(app, user, film):
    db.session.add(
        UserFilmImage(
            user_id=user.id,
            film_id=film.tmdb_id,
            poster_path="/poster-a.jpg",
            backdrop_path="/back-a.jpg",
        )
    )
    db.session.commit()

    assert effective_poster_url(film, user).endswith("/poster-a.jpg")
    assert effective_backdrop_url(film, user).endswith("/back-a.jpg")

    bob = User(username="bob", email="bob@example.com")
    bob.set_password("password123")
    db.session.add(bob)
    db.session.commit()
    assert effective_poster_url(film, bob).endswith("/default-poster.jpg")


def test_profile_backdrop_save_and_remove(auth_client, user, film, monkeypatch):
    monkeypatch.setattr("app.api.routes.get_movie_images", _fake_images)

    resp = auth_client.post(
        "/api/profile/backdrop",
        json={"tmdb_id": film.tmdb_id, "backdrop_path": "/back-a.jpg"},
    )
    assert resp.status_code == 200
    assert db.session.get(User, user.id).backdrop_url.endswith("/back-a.jpg")

    resp = auth_client.delete("/api/profile/backdrop")
    assert resp.status_code == 200
    assert db.session.get(User, user.id).backdrop_url is None


def test_film_image_override_set_and_reset(auth_client, user, film, monkeypatch):
    monkeypatch.setattr("app.api.routes.get_movie_images", _fake_images)

    resp = auth_client.patch(
        f"/api/film-images/{film.tmdb_id}",
        json={"field": "poster", "path": "/poster-a.jpg"},
    )
    assert resp.status_code == 200
    override = UserFilmImage.query.filter_by(user_id=user.id, film_id=film.tmdb_id).one()
    assert override.poster_path == "/poster-a.jpg"

    resp = auth_client.patch(
        f"/api/film-images/{film.tmdb_id}",
        json={"field": "poster", "path": None},
    )
    assert resp.status_code == 200
    assert UserFilmImage.query.filter_by(user_id=user.id, film_id=film.tmdb_id).first() is None


def test_override_is_per_user(client, user, film, monkeypatch):
    monkeypatch.setattr("app.api.routes.get_movie_images", _fake_images)
    bob = User(username="bob", email="bob@example.com")
    bob.set_password("password123")
    db.session.add(bob)
    db.session.commit()

    client.post("/login", data={"identifier": "bob", "password": "password123"})
    resp = client.patch(
        f"/api/film-images/{film.tmdb_id}",
        json={"field": "backdrop", "path": "/back-b.jpg"},
    )
    assert resp.status_code == 200

    assert UserFilmImage.query.filter_by(user_id=bob.id, film_id=film.tmdb_id).one()
    assert UserFilmImage.query.filter_by(user_id=user.id, film_id=film.tmdb_id).first() is None


def test_logging_new_film_upserts_current_entry(auth_client, user, film):
    auth_client.post("/api/logs", json={"tmdb_id": film.tmdb_id, "rating": 10})
    auth_client.post("/api/logs", json={"tmdb_id": film.tmdb_id, "liked": True})
    auth_client.post("/api/logs", json={"tmdb_id": film.tmdb_id, "review": "Still one row."})

    logs = LogEntry.query.filter_by(user_id=user.id, film_id=film.tmdb_id).all()
    assert len(logs) == 1
    assert logs[0].rating == 10
    assert logs[0].liked is True
    assert logs[0].review == "Still one row."

    auth_client.post(
        "/api/logs",
        json={"tmdb_id": film.tmdb_id, "rating": 8, "is_rewatch": True},
    )
    assert LogEntry.query.filter_by(user_id=user.id, film_id=film.tmdb_id).count() == 2


def test_profile_restores_header_sections_and_sidebar(auth_client, user, film):
    db.session.add(LogEntry(user_id=user.id, film_id=film.tmdb_id, rating=8, liked=True, review="A restored row."))
    db.session.commit()

    resp = auth_client.get(f"/{user.username}")
    body = resp.data.decode()

    for text in [
        "Favourite films",
        "Recent activity",
        "Diary",
        "Watchlist",
        "Ratings",
        "Recent reviews",
        "@alice",
    ]:
        assert text in body


def test_search_includes_accounts(auth_client, user):
    resp = auth_client.get("/api/search?q=ali")
    assert resp.status_code == 200
    assert resp.get_json()["users"][0]["username"] == "alice"


def test_reviews_page_is_dedicated(auth_client, user, film):
    db.session.add(LogEntry(user_id=user.id, film_id=film.tmdb_id, review="Own page."))
    db.session.commit()

    resp = auth_client.get(f"/{user.username}/reviews")
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "Reviews" in body
    assert "Own page." in body


def test_films_page_is_dedicated(auth_client, user, film):
    db.session.add(LogEntry(user_id=user.id, film_id=film.tmdb_id, rating=9))
    db.session.commit()

    resp = auth_client.get(f"/{user.username}/films")
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "All films alice has logged." in body
    assert film.title in body


def test_avatar_upload_updates_profile(auth_client, user):
    resp = auth_client.post(
        "/settings",
        data={
            "form_type": "profile",
            "avatar_file": (io.BytesIO(b"not-really-image"), "avatar.png"),
        },
        content_type="multipart/form-data",
    )
    assert resp.status_code == 302
    assert db.session.get(User, user.id).avatar_url.startswith("/uploads/")


def test_profile_avatar_opens_lightbox(auth_client, user):
    user.avatar_url = "https://example.com/avatar.jpg"
    db.session.commit()

    resp = auth_client.get(f"/{user.username}")
    body = resp.data.decode()

    assert resp.status_code == 200
    assert "data-avatar-open" in body
    assert 'id="avatar-dialog"' in body
    assert "https://example.com/avatar.jpg" in body
    assert "#ff8000" not in body


def test_actor_page_and_cast_links(auth_client, film, monkeypatch):
    def fake_get_film_credits(_tmdb_id):
        return [
            {
                "id": 500,
                "name": "Ryan Gosling",
                "character": "Driver",
                "profile_url": "https://image.tmdb.org/t/p/w185/profile.jpg",
            }
        ]

    def fake_get_person(_person_id):
        return {
            "id": 500,
            "name": "Ryan Gosling",
            "biography": "Canadian actor.",
            "birthday": "1980-11-12",
            "deathday": None,
            "place_of_birth": "London, Ontario, Canada",
            "known_for_department": "Acting",
            "profile_url": "https://image.tmdb.org/t/p/h632/profile.jpg",
            "tmdb_url": "https://www.themoviedb.org/person/500",
        }

    def fake_get_person_movie_credits(_person_id):
        return [
            {
                "tmdb_id": film.tmdb_id,
                "title": film.title,
                "release_year": film.release_year,
                "poster_path": film.poster_path,
                "character": "Driver",
                "popularity": 10,
            }
        ]

    monkeypatch.setattr("app.films.routes.get_film_credits", fake_get_film_credits)
    monkeypatch.setattr("app.people.routes.get_person", fake_get_person)
    monkeypatch.setattr("app.people.routes.get_person_movie_credits", fake_get_person_movie_credits)

    film_resp = auth_client.get(f"/film/{film.tmdb_id}")
    assert film_resp.status_code == 200
    assert '/people/500' in film_resp.data.decode()

    person_resp = auth_client.get("/people/500")
    body = person_resp.data.decode()
    assert person_resp.status_code == 200
    assert "Films starring" in body
    assert "Ryan Gosling" in body
    assert film.title in body


def test_trending_uses_custom_poster(auth_client, user, film, monkeypatch):
    db.session.add(
        UserFilmImage(
            user_id=user.id,
            film_id=film.tmdb_id,
            poster_path="/custom-trending.jpg",
        )
    )
    db.session.commit()

    monkeypatch.setattr(
        "app.films.routes.trending_movies",
        lambda: [
            {
                "tmdb_id": film.tmdb_id,
                "title": film.title,
                "release_year": film.release_year,
                "poster_path": film.poster_path,
            }
        ],
    )

    resp = auth_client.get("/")
    body = resp.data.decode()
    assert resp.status_code == 200
    assert "/custom-trending.jpg" in body


def test_letterboxd_import_zip(auth_client, user, monkeypatch):
    imported_film = Film(
        tmdb_id=321,
        title="Imported Movie",
        release_year=2024,
        poster_path="/imported.jpg",
    )
    watchlist_film = Film(
        tmdb_id=654,
        title="Watch Later",
        release_year=2025,
        poster_path="/watch.jpg",
    )
    db.session.add_all([imported_film, watchlist_film])
    db.session.commit()

    def fake_search_movies(query, page=1):
        if query == "Imported Movie":
            return {"results": [{"tmdb_id": 321, "title": query, "release_year": 2024}], "page": 1, "total_pages": 1}
        if query == "Watch Later":
            return {"results": [{"tmdb_id": 654, "title": query, "release_year": 2025}], "page": 1, "total_pages": 1}
        return {"results": [], "page": 1, "total_pages": 0}

    monkeypatch.setattr("app.letterboxd_import.search_movies", fake_search_movies)
    monkeypatch.setattr("app.letterboxd_import.ensure_film_cached", lambda tmdb_id: db.session.get(Film, tmdb_id))

    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr(
            "letterboxd-export/reviews.csv",
            "Date,Name,Year,Letterboxd URI,Rating,Rewatch,Review,Tags,Watched Date\n"
            "2026-01-02,Imported Movie,2024,https://boxd.it/test,4.5,,Great import,,2026-01-01\n",
        )
        archive.writestr(
            "letterboxd-export/likes/films.csv",
            "Date,Name,Year,Letterboxd URI\n"
            "2026-01-02,Imported Movie,2024,https://boxd.it/test\n",
        )
        archive.writestr(
            "letterboxd-export/watchlist.csv",
            "Date,Name,Year,Letterboxd URI\n"
            "2026-01-03,Watch Later,2025,https://boxd.it/watch\n",
        )
    payload.seek(0)

    preview_resp = auth_client.post(
        "/settings",
        data={
            "form_type": "letterboxd_preview",
            "letterboxd_export": (payload, "letterboxd-export.zip"),
        },
        content_type="multipart/form-data",
    )
    assert preview_resp.status_code == 200
    body = preview_resp.data.decode()
    assert "Ready to import" in body
    token = re.search(r'name="import_token" value="([^"]+)"', body).group(1)

    resp = auth_client.post(
        "/settings",
        data={
            "form_type": "letterboxd_import",
            "import_token": token,
        },
    )

    assert resp.status_code == 302
    log = LogEntry.query.filter_by(user_id=user.id, film_id=321).one()
    assert log.rating == 9
    assert log.review == "Great import"
    assert log.liked is True
    assert WatchlistItem.query.filter_by(user_id=user.id, film_id=654).one()


def test_diary_filters_by_rating_and_liked(auth_client, user, film):
    second = Film(tmdb_id=12, title="Lower Rated", release_year=2023)
    db.session.add_all(
        [
            second,
            LogEntry(user_id=user.id, film_id=film.tmdb_id, rating=10, liked=True),
            LogEntry(user_id=user.id, film_id=second.tmdb_id, rating=4, liked=False),
        ]
    )
    db.session.commit()

    resp = auth_client.get(f"/{user.username}/diary?rating=10&filter=liked")
    body = resp.data.decode()

    assert resp.status_code == 200
    assert film.title in body
    assert second.title not in body


def test_stats_page_renders_profile_stats(auth_client, user, film):
    db.session.add(LogEntry(user_id=user.id, film_id=film.tmdb_id, rating=9, liked=True))
    db.session.commit()

    resp = auth_client.get(f"/{user.username}/stats")
    body = resp.data.decode()

    assert resp.status_code == 200
    assert "Highest rated" in body
    assert "Average" in body
    assert film.title in body


def test_favorite_films_are_set_from_settings(auth_client, user, film, monkeypatch):
    second = Film(
        tmdb_id=11,
        title="Second Favorite",
        release_year=2024,
        poster_path="/second.jpg",
    )
    db.session.add(second)
    db.session.add(LogEntry(user_id=user.id, film_id=film.tmdb_id, rating=8))
    db.session.commit()

    monkeypatch.setattr("app.users.routes.ensure_film_cached", lambda tmdb_id: db.session.get(Film, tmdb_id))

    resp = auth_client.post(
        "/settings",
        data={
            "form_type": "profile",
            "favorite_tmdb_ids": [str(second.tmdb_id)],
        },
    )
    assert resp.status_code == 302

    favorites = UserFavoriteFilm.query.filter_by(user_id=user.id).all()
    assert [favorite.film_id for favorite in favorites] == [second.tmdb_id]

    profile = auth_client.get(f"/{user.username}").data.decode()
    assert "Second Favorite" in profile


def test_favorite_films_save_with_uploaded_avatar_path(auth_client, user, film, monkeypatch):
    user.avatar_url = "/uploads/avatar.png"
    db.session.commit()
    monkeypatch.setattr("app.users.routes.ensure_film_cached", lambda tmdb_id: db.session.get(Film, tmdb_id))

    resp = auth_client.post(
        "/settings",
        data={
            "form_type": "profile",
            "avatar_url": user.avatar_url,
            "favorite_tmdb_ids": [str(film.tmdb_id)],
        },
    )

    assert resp.status_code == 302
    assert UserFavoriteFilm.query.filter_by(user_id=user.id, film_id=film.tmdb_id).one()
