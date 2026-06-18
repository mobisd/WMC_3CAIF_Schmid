from __future__ import annotations

from datetime import date, timedelta

from app.extensions import db
from app.models import LogEntry


def test_quick_actions_upsert_current_entry(auth_client, user, film):
    resp = auth_client.post("/api/logs", json={"tmdb_id": film.tmdb_id, "rating": 10})
    assert resp.status_code == 201

    resp = auth_client.post("/api/logs", json={"tmdb_id": film.tmdb_id, "liked": True})
    assert resp.status_code == 200

    resp = auth_client.post(
        "/api/logs", json={"tmdb_id": film.tmdb_id, "review": "Dreamy."}
    )
    assert resp.status_code == 200

    logs = LogEntry.query.filter_by(user_id=user.id, film_id=film.tmdb_id).all()
    assert len(logs) == 1
    assert logs[0].rating == 10
    assert logs[0].liked is True
    assert logs[0].review == "Dreamy."
    assert logs[0].watched_on == date.today()


def test_editing_rating_or_review_keeps_one_entry(auth_client, user, film):
    auth_client.post(
        "/api/logs",
        json={"tmdb_id": film.tmdb_id, "rating": 10, "review": "First take."},
    )

    auth_client.post("/api/logs", json={"tmdb_id": film.tmdb_id, "rating": 8})
    auth_client.post(
        "/api/logs", json={"tmdb_id": film.tmdb_id, "review": "Second take."}
    )

    logs = LogEntry.query.filter_by(user_id=user.id, film_id=film.tmdb_id).all()
    assert len(logs) == 1
    assert logs[0].rating == 8
    assert logs[0].review == "Second take."

    auth_client.post("/api/logs", json={"tmdb_id": film.tmdb_id, "rating": None})
    log = LogEntry.query.filter_by(user_id=user.id, film_id=film.tmdb_id).one()
    assert log.rating is None


def test_explicit_rewatch_creates_second_diary_row(auth_client, user, film):
    first_day = date.today() - timedelta(days=1)
    today = date.today()

    auth_client.post(
        "/api/logs",
        json={
            "tmdb_id": film.tmdb_id,
            "rating": 7,
            "watched_on": first_day.isoformat(),
        },
    )
    resp = auth_client.post(
        "/api/logs",
        json={
            "tmdb_id": film.tmdb_id,
            "rating": 9,
            "watched_on": today.isoformat(),
            "is_rewatch": True,
        },
    )
    assert resp.status_code == 201

    logs = (
        LogEntry.query.filter_by(user_id=user.id, film_id=film.tmdb_id)
        .order_by(LogEntry.watched_on.desc(), LogEntry.created_at.desc())
        .all()
    )
    assert len(logs) == 2
    assert logs[0].watched_on == today
    assert logs[0].is_rewatch is True
    assert logs[1].watched_on == first_day

    resp = auth_client.get(f"/{user.username}/diary")
    body = resp.data.decode()
    assert body.count(film.title) >= 2
    assert "rewatch" in body
