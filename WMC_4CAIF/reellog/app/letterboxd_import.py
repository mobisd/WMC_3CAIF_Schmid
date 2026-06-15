"""Import a Letterboxd export ZIP into ReelLog."""
from __future__ import annotations

import csv
import io
import zipfile
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Iterable

from .extensions import db
from .models import Film, LogEntry, User, WatchlistItem
from .tmdb import ensure_film_cached, search_movies


class LetterboxdImportError(Exception):
    """Raised when an uploaded export cannot be read."""


@dataclass
class ImportSummary:
    logs_added: int = 0
    logs_updated: int = 0
    watchlist_added: int = 0
    films_skipped: int = 0


@dataclass
class ImportPreview:
    diary_rows: int = 0
    review_rows: int = 0
    rating_rows: int = 0
    watched_rows: int = 0
    watchlist_rows: int = 0
    liked_rows: int = 0

    @property
    def total_rows(self) -> int:
        return (
            self.diary_rows
            + self.review_rows
            + self.rating_rows
            + self.watched_rows
            + self.watchlist_rows
            + self.liked_rows
        )


def import_letterboxd_zip(file_storage, user: User) -> ImportSummary:
    return import_letterboxd_bytes(file_storage.read(), user)


def import_letterboxd_bytes(raw: bytes, user: User) -> ImportSummary:
    if not raw:
        raise LetterboxdImportError("Choose a Letterboxd export ZIP.")

    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile as exc:
        raise LetterboxdImportError("That file is not a valid ZIP export.") from exc

    with archive:
        importer = _Importer(archive, user)
        return importer.run()


def preview_letterboxd_zip(raw: bytes) -> ImportPreview:
    if not raw:
        raise LetterboxdImportError("Choose a Letterboxd export ZIP.")

    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile as exc:
        raise LetterboxdImportError("That file is not a valid ZIP export.") from exc

    with archive:
        reader = _ArchiveReader(archive)
        return ImportPreview(
            diary_rows=reader.row_count("diary.csv"),
            review_rows=reader.row_count("reviews.csv"),
            rating_rows=reader.row_count("ratings.csv"),
            watched_rows=reader.row_count("watched.csv"),
            watchlist_rows=reader.row_count("watchlist.csv"),
            liked_rows=reader.row_count("likes/films.csv"),
        )


class _ArchiveReader:
    def __init__(self, archive: zipfile.ZipFile):
        self.archive = archive

    def row_count(self, suffix: str) -> int:
        return len(self.rows(suffix))

    def rows(self, suffix: str) -> list[dict[str, str]]:
        name = self.find_member(suffix)
        if not name:
            return []
        with self.archive.open(name) as handle:
            text = io.TextIOWrapper(handle, encoding="utf-8-sig", newline="")
            return list(csv.DictReader(text))

    def find_member(self, suffix: str) -> str | None:
        suffix = suffix.replace("\\", "/").lower()
        for name in self.archive.namelist():
            if name.replace("\\", "/").lower().endswith(suffix):
                return name
        return None


class _Importer:
    def __init__(self, archive: zipfile.ZipFile, user: User):
        self.archive = archive
        self.user = user
        self.summary = ImportSummary()
        self.reader = _ArchiveReader(archive)
        self._film_cache: dict[tuple[str, int | None], Film | None] = {}

    def run(self) -> ImportSummary:
        liked = {self._film_key(row) for row in self._rows("likes/films.csv")}

        for row in self._rows("diary.csv"):
            self._import_log_row(row, liked)
        for row in self._rows("reviews.csv"):
            self._import_log_row(row, liked)
        for row in self._rows("ratings.csv"):
            self._import_current_row(row, liked, rating_only=True)
        for row in self._rows("watched.csv"):
            self._import_current_row(row, liked)
        for row in self._rows("watchlist.csv"):
            self._import_watchlist_row(row)

        db.session.commit()
        return self.summary

    def _rows(self, suffix: str) -> Iterable[dict[str, str]]:
        return self.reader.rows(suffix)

    def _film_key(self, row: dict[str, str]) -> tuple[str, int | None]:
        return ((row.get("Name") or "").strip().casefold(), _parse_year(row.get("Year")))

    def _resolve_film(self, row: dict[str, str]) -> Film | None:
        title = (row.get("Name") or "").strip()
        year = _parse_year(row.get("Year"))
        key = (title.casefold(), year)
        if not title:
            return None
        if key in self._film_cache:
            return self._film_cache[key]

        existing = Film.query.filter_by(title=title, release_year=year).first()
        if existing:
            self._film_cache[key] = existing
            return existing

        results = search_movies(title).get("results", [])
        candidate = None
        if year is not None:
            candidate = next((item for item in results if item.get("release_year") == year), None)
        if candidate is None and results:
            candidate = results[0]
        if candidate is None:
            self.summary.films_skipped += 1
            self._film_cache[key] = None
            return None

        film = ensure_film_cached(candidate["tmdb_id"])
        if film is None:
            self.summary.films_skipped += 1
        self._film_cache[key] = film
        return film

    def _import_log_row(self, row: dict[str, str], liked: set[tuple[str, int | None]]) -> None:
        film = self._resolve_film(row)
        if film is None:
            return

        watched_on = _parse_date(row.get("Watched Date")) or _parse_date(row.get("Date"))
        rating = _parse_rating(row.get("Rating"))
        review = (row.get("Review") or "").strip() or None
        is_liked = self._film_key(row) in liked
        is_rewatch = _parse_bool(row.get("Rewatch"))

        duplicate = LogEntry.query.filter_by(
            user_id=self.user.id,
            film_id=film.tmdb_id,
            watched_on=watched_on,
            rating=rating,
            review=review,
        ).first()
        if duplicate:
            changed = False
            if is_liked and not duplicate.liked:
                duplicate.liked = True
                changed = True
            if is_rewatch and not duplicate.is_rewatch:
                duplicate.is_rewatch = True
                changed = True
            if changed:
                self.summary.logs_updated += 1
            return

        db.session.add(
            LogEntry(
                user_id=self.user.id,
                film_id=film.tmdb_id,
                watched_on=watched_on,
                rating=rating,
                review=review,
                liked=is_liked,
                is_rewatch=is_rewatch,
            )
        )
        self.summary.logs_added += 1

    def _import_current_row(
        self,
        row: dict[str, str],
        liked: set[tuple[str, int | None]],
        rating_only: bool = False,
    ) -> None:
        film = self._resolve_film(row)
        if film is None:
            return

        log = (
            LogEntry.query.filter_by(user_id=self.user.id, film_id=film.tmdb_id)
            .order_by(LogEntry.created_at.desc(), LogEntry.id.desc())
            .first()
        )
        added = False
        if log is None:
            log = LogEntry(user_id=self.user.id, film_id=film.tmdb_id)
            db.session.add(log)
            self.summary.logs_added += 1
            added = True

        changed = False
        rating = _parse_rating(row.get("Rating"))
        if rating is not None and log.rating != rating:
            log.rating = rating
            changed = True
        if self._film_key(row) in liked and not log.liked:
            log.liked = True
            changed = True
        if not rating_only and log.watched_on is None:
            log.watched_on = _parse_date(row.get("Date"))
            changed = True
        if changed and not added:
            self.summary.logs_updated += 1

    def _import_watchlist_row(self, row: dict[str, str]) -> None:
        film = self._resolve_film(row)
        if film is None:
            return

        exists = WatchlistItem.query.filter_by(user_id=self.user.id, film_id=film.tmdb_id).first()
        if exists:
            return
        db.session.add(WatchlistItem(user_id=self.user.id, film_id=film.tmdb_id))
        self.summary.watchlist_added += 1


def _parse_year(value: str | None) -> int | None:
    try:
        return int(value) if value else None
    except ValueError:
        return None


def _parse_date(value: str | None):
    value = (value or "").strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_rating(value: str | None) -> int | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return int(Decimal(value) * 2)
    except (InvalidOperation, ValueError):
        return None


def _parse_bool(value: str | None) -> bool:
    return (value or "").strip().casefold() in {"yes", "true", "1", "rewatch"}
