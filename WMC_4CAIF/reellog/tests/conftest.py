from __future__ import annotations

import os

# Test-Umgebung: eigene Secrets setzen, damit keine echte .env noetig ist.
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("TMDB_API_KEY", "test-tmdb")

import pytest

from app import create_app
from app.config import Config
from app.extensions import db
from app.models import Film, User


class TestConfig(Config):
    # Tests laufen mit einer frischen In-Memory-Datenbank.
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SERVER_NAME = "localhost"


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def user(app):
    u = User(username="alice", email="alice@example.com")
    u.set_password("password123")
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def auth_client(client, user):
    # Client ist danach schon eingeloggt.
    client.post("/login", data={"identifier": "alice", "password": "password123"})
    return client


@pytest.fixture
def film(app):
    f = Film(
        tmdb_id=10,
        title="Obsession Test",
        release_year=1976,
        poster_path="/default-poster.jpg",
        backdrop_path="/default-backdrop.jpg",
    )
    db.session.add(f)
    db.session.commit()
    return f
