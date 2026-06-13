"""SQLAlchemy models for ReelLog.

Design notes:
- Ratings are stored as an INTEGER 1..10 (each unit = half a star). This avoids
  floating-point precision bugs entirely; we only convert to 0.5..5.0 at the
  display/input edge via the `stars` helper.
- A film is "watched" by a user iff >=1 LogEntry exists for that (user, film).
- A user's current rating for a film = rating of their most recent rated log.
"""
from __future__ import annotations

from datetime import date, datetime

from flask import current_app
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager


@login_manager.user_loader
def load_user(user_id: str):
    # Flask-Login stores the id as a string in the session cookie.
    return db.session.get(User, int(user_id))


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(80), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    avatar_url = db.Column(db.String(500), nullable=True)
    backdrop_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # ordered newest-first so templates can iterate directly.
    logs = db.relationship(
        "LogEntry",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="LogEntry.created_at.desc()",
    )
    watchlist = db.relationship(
        "WatchlistItem",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="WatchlistItem.added_at.desc()",
    )

    # --- password helpers (never store or return plaintext) --------------
    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    # --- display helpers --------------------------------------------------
    @property
    def name(self) -> str:
        return self.display_name or self.username

    # --- stats (computed in Python from already-loaded relationships) -----
    @property
    def films_watched(self) -> int:
        return len({log.film_id for log in self.logs})

    @property
    def films_watched_this_year(self) -> int:
        year = date.today().year
        return len(
            {
                log.film_id
                for log in self.logs
                if log.watched_on and log.watched_on.year == year
            }
        )

    @property
    def review_count(self) -> int:
        return sum(1 for log in self.logs if (log.review or "").strip())

    def rating_for(self, film_id: int):
        """Most recent rating (int 1..10) the user gave this film, or None."""
        for log in self.logs:  # logs are ordered newest-first
            if log.film_id == film_id and log.rating is not None:
                return log.rating
        return None

    def has_watched(self, film_id: int) -> bool:
        return any(log.film_id == film_id for log in self.logs)

    def in_watchlist(self, film_id: int) -> bool:
        return any(item.film_id == film_id for item in self.watchlist)


class Film(db.Model):
    """Local cache of TMDB movie data.

    Storing films locally gives us stable foreign keys for logs/watchlist and
    shields us from TMDB rate limits/outages.
    """

    __tablename__ = "films"

    tmdb_id = db.Column(db.Integer, primary_key=True)  # from TMDB, no autoincrement
    title = db.Column(db.String(300), nullable=False)
    release_year = db.Column(db.Integer, nullable=True)
    poster_path = db.Column(db.String(255), nullable=True)
    backdrop_path = db.Column(db.String(255), nullable=True)
    overview = db.Column(db.Text, nullable=True)
    runtime = db.Column(db.Integer, nullable=True)
    tmdb_rating = db.Column(db.Float, nullable=True)
    director = db.Column(db.String(200), nullable=True)
    cached_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    logs = db.relationship("LogEntry", back_populates="film")
    watchlist_items = db.relationship("WatchlistItem", back_populates="film")

    # --- image URL helpers (fall back to local placeholders) -------------
    def poster_url(self, size: str = "w342") -> str:
        from flask import url_for

        if self.poster_path:
            base = current_app.config["TMDB_IMAGE_BASE"]
            return f"{base}/{size}{self.poster_path}"
        return url_for("static", filename="img/poster-fallback.svg")

    def backdrop_url(self, size: str = "w1280") -> str:
        from flask import url_for

        if self.backdrop_path:
            base = current_app.config["TMDB_IMAGE_BASE"]
            return f"{base}/{size}{self.backdrop_path}"
        return url_for("static", filename="img/backdrop-fallback.svg")

    @property
    def is_stale(self) -> bool:
        age_days = (datetime.utcnow() - self.cached_at).days
        return age_days >= current_app.config["TMDB_CACHE_DAYS"]


class WatchlistItem(db.Model):
    __tablename__ = "watchlist_items"
    __table_args__ = (
        db.UniqueConstraint("user_id", "film_id", name="uq_watchlist_user_film"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    film_id = db.Column(db.Integer, db.ForeignKey("films.tmdb_id"), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="watchlist")
    film = db.relationship("Film", back_populates="watchlist_items")


class LogEntry(db.Model):
    """One diary entry. Powers watched / rated / logged-by-date / reviewed."""

    __tablename__ = "log_entries"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    film_id = db.Column(db.Integer, db.ForeignKey("films.tmdb_id"), nullable=False)
    watched_on = db.Column(db.Date, nullable=True)  # null => date unknown
    rating = db.Column(db.Integer, nullable=True)  # 1..10 half-star units
    review = db.Column(db.Text, nullable=True)
    liked = db.Column(db.Boolean, default=False, nullable=False)
    is_rewatch = db.Column(db.Boolean, default=False, nullable=False)
    contains_spoilers = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="logs")
    film = db.relationship("Film", back_populates="logs")

    @property
    def stars(self):
        """Rating as a float 0.5..5.0, or None. Display/edit edge only."""
        return None if self.rating is None else self.rating / 2

    @property
    def has_review(self) -> bool:
        return bool((self.review or "").strip())
