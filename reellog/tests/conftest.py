"""Shared pytest fixtures.

We set the required secrets as env vars *before* importing the app, because
app.config.Config reads them at class-definition time (fail-fast design).
Tests run against an in-memory SQLite DB with CSRF disabled.
"""
from __future__ import annotations

import os
import shutil
import tempfile

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("TMDB_API_KEY", "test-tmdb-key")

import pytest  # noqa: E402

from app import create_app  # noqa: E402
from app.config import Config  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import Film, User  # noqa: E402


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    TAILWIND_CDN = False
    SERVER_NAME = "localhost"


@pytest.fixture
def app():
    upload_dir = tempfile.mkdtemp(prefix="reellog-test-uploads-")
    app = create_app(TestConfig)
    # Point uploads at a throwaway dir so tests never write into the repo.
    app.config["UPLOAD_DIR"] = upload_dir
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()
    shutil.rmtree(upload_dir, ignore_errors=True)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def user(app):
    u = User(username="alice", email="alice@example.com", display_name="Alice")
    u.set_password("password123")
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def auth_client(client, user):
    client.post(
        "/login",
        data={"identifier": "alice", "password": "password123"},
        follow_redirects=True,
    )
    return client


@pytest.fixture
def film(app):
    """A fresh, cached film so get_film() never hits the network."""
    f = Film(
        tmdb_id=27205,
        title="Inception",
        release_year=2010,
        poster_path="/poster.jpg",
        backdrop_path="/backdrop.jpg",
        overview="A thief who steals corporate secrets.",
        runtime=148,
        tmdb_rating=8.4,
        director="Christopher Nolan",
    )
    db.session.add(f)
    db.session.commit()
    return f
