"""Users blueprint: public profiles, diary, watchlist, and settings.

The /<username> route is a catch-all, so this blueprint is registered LAST in
the app factory. Reserved usernames (api, film, ...) can never be created, so
they can never shadow real routes here.
"""
from __future__ import annotations

from collections import Counter
from datetime import date
from pathlib import Path
import secrets

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload

from ..config import Config
from ..extensions import db
from ..letterboxd_import import (
    LetterboxdImportError,
    import_letterboxd_bytes,
    preview_letterboxd_zip,
)
from ..models import LogEntry, User, UserFavoriteFilm, WatchlistItem
from ..tmdb import TMDBError, ensure_film_cached
from ..uploads import UploadError, save_avatar
from ..validators import normalise_username, password_error, url_error

users_bp = Blueprint("users", __name__)


def _get_user_or_404(username: str) -> User:
    username = normalise_username(username)
    user = User.query.filter_by(username=username).first()
    if user is None:
        abort(404)
    return user


@users_bp.route("/<username>")
def profile(username: str):
    user = _get_user_or_404(username)
    recent_logs = (
        LogEntry.query.options(joinedload(LogEntry.film))
        .filter_by(user_id=user.id)
        .order_by(LogEntry.created_at.desc())
        .limit(12)
        .all()
    )
    reviews = [
        log
        for log in (
            LogEntry.query.options(joinedload(LogEntry.film))
            .filter(LogEntry.user_id == user.id, LogEntry.review.isnot(None))
            .order_by(LogEntry.created_at.desc())
            .limit(6)
            .all()
        )
        if log.has_review
    ]
    diary_preview = (
        LogEntry.query.options(joinedload(LogEntry.film))
        .filter(LogEntry.user_id == user.id, LogEntry.watched_on.isnot(None))
        .order_by(LogEntry.watched_on.desc(), LogEntry.created_at.desc())
        .limit(6)
        .all()
    )
    watchlist_preview = (
        WatchlistItem.query.options(joinedload(WatchlistItem.film))
        .filter_by(user_id=user.id)
        .order_by(WatchlistItem.added_at.desc())
        .limit(6)
        .all()
    )
    histogram = [0] * 10
    for log in user.logs:
        if log.rating:
            histogram[log.rating - 1] += 1

    favorite_films = [item.film for item in user.favorite_films]

    return render_template(
        "profile.html",
        user=user,
        recent_logs=recent_logs,
        reviews=reviews,
        diary_preview=diary_preview,
        watchlist_preview=watchlist_preview,
        histogram=histogram,
        favorite_films=favorite_films,
    )


@users_bp.route("/<username>/diary")
def diary(username: str):
    user = _get_user_or_404(username)
    query = (
        LogEntry.query.options(joinedload(LogEntry.film))
        .filter_by(user_id=user.id)
    )
    selected_year = request.args.get("year", "")
    selected_rating = request.args.get("rating", "")
    selected_flag = request.args.get("filter", "")

    if selected_year:
        try:
            year = int(selected_year)
        except ValueError:
            year = None
        if year:
            query = query.filter(
                LogEntry.watched_on >= date(year, 1, 1),
                LogEntry.watched_on <= date(year, 12, 31),
            )

    if selected_rating:
        try:
            rating = int(selected_rating)
        except ValueError:
            rating = None
        if rating and 1 <= rating <= 10:
            query = query.filter(LogEntry.rating == rating)

    if selected_flag == "liked":
        query = query.filter(LogEntry.liked.is_(True))
    elif selected_flag == "reviewed":
        query = query.filter(LogEntry.review.isnot(None), LogEntry.review != "")
    elif selected_flag == "rewatches":
        query = query.filter(LogEntry.is_rewatch.is_(True))

    logs = query.order_by(
        LogEntry.watched_on.desc().nullslast(),
        LogEntry.created_at.desc(),
    ).all()
    years = sorted(
        {log.watched_on.year for log in user.logs if log.watched_on},
        reverse=True,
    )
    return render_template(
        "diary.html",
        user=user,
        logs=logs,
        years=years,
        selected_year=selected_year,
        selected_rating=selected_rating,
        selected_flag=selected_flag,
    )


@users_bp.route("/<username>/films")
def films(username: str):
    user = _get_user_or_404(username)
    logs = (
        LogEntry.query.options(joinedload(LogEntry.film))
        .filter_by(user_id=user.id)
        .order_by(LogEntry.created_at.desc())
        .all()
    )
    seen = set()
    films = []
    for log in logs:
        if log.film_id in seen:
            continue
        seen.add(log.film_id)
        films.append(log.film)
    return render_template("films.html", user=user, films=films)


@users_bp.route("/<username>/watchlist")
def watchlist(username: str):
    user = _get_user_or_404(username)
    items = (
        WatchlistItem.query.options(joinedload(WatchlistItem.film))
        .filter_by(user_id=user.id)
        .order_by(WatchlistItem.added_at.desc())
        .all()
    )
    return render_template("watchlist.html", user=user, items=items)


@users_bp.route("/<username>/reviews")
def reviews(username: str):
    user = _get_user_or_404(username)
    items = [
        log
        for log in (
            LogEntry.query.options(joinedload(LogEntry.film))
            .filter(LogEntry.user_id == user.id, LogEntry.review.isnot(None))
            .order_by(LogEntry.created_at.desc())
            .all()
        )
        if log.has_review
    ]
    return render_template("reviews.html", user=user, reviews=items)


@users_bp.route("/<username>/stats")
def stats(username: str):
    user = _get_user_or_404(username)
    logs = (
        LogEntry.query.options(joinedload(LogEntry.film))
        .filter_by(user_id=user.id)
        .order_by(LogEntry.watched_on.desc().nullslast(), LogEntry.created_at.desc())
        .all()
    )
    rated_logs = [log for log in logs if log.rating]
    histogram = [0] * 10
    for log in rated_logs:
        histogram[log.rating - 1] += 1

    year_counts = Counter(log.watched_on.year for log in logs if log.watched_on)
    top_years = sorted(year_counts.items(), key=lambda item: item[0], reverse=True)
    director_counts = Counter(
        log.film.director for log in logs if log.film and log.film.director
    )
    top_directors = director_counts.most_common(6)
    highest_rated = sorted(
        rated_logs,
        key=lambda log: (log.rating or 0, log.watched_on or log.created_at.date()),
        reverse=True,
    )[:8]
    average_rating = (
        sum(log.rating for log in rated_logs) / len(rated_logs) / 2 if rated_logs else None
    )
    unique_films = len({log.film_id for log in logs})

    return render_template(
        "stats.html",
        user=user,
        logs=logs,
        histogram=histogram,
        top_years=top_years,
        top_directors=top_directors,
        highest_rated=highest_rated,
        average_rating=average_rating,
        unique_films=unique_films,
        liked_count=sum(1 for log in logs if log.liked),
        rewatch_count=sum(1 for log in logs if log.is_rewatch),
    )


@users_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    if request.method == "POST":
        form_type = request.form.get("form_type", "profile")

        if form_type == "password":
            return _handle_password_change()
        if form_type == "letterboxd_preview":
            return _handle_letterboxd_preview()
        if form_type == "letterboxd_import":
            return _handle_letterboxd_import()
        return _handle_profile_update()

    return render_template("settings.html", user=current_user)


def _handle_profile_update():
    display_name = request.form.get("display_name", "").strip() or None
    bio = request.form.get("bio", "").strip() or None
    avatar_url = request.form.get("avatar_url", "").strip() or None

    errors = []
    if bio and len(bio) > Config.BIO_MAX_LEN:
        errors.append(f"Bio is too long (max {Config.BIO_MAX_LEN} characters).")
    if display_name and len(display_name) > 80:
        errors.append("Display name is too long (max 80 characters).")
    err = url_error(avatar_url or "", Config.URL_MAX_LEN)
    if err:
        errors.append(f"Avatar {err}")
    uploaded_avatar = request.files.get("avatar_file")
    if uploaded_avatar and uploaded_avatar.filename:
        try:
            avatar_url = save_avatar(uploaded_avatar)
        except UploadError as exc:
            errors.append(str(exc))

    if errors:
        for e in errors:
            flash(e, "error")
        return render_template("settings.html", user=current_user), 422

    try:
        _replace_favorite_films(request.form.getlist("favorite_tmdb_ids"))
    except ValueError as exc:
        flash(str(exc), "error")
        return render_template("settings.html", user=current_user), 422

    current_user.display_name = display_name
    current_user.bio = bio
    current_user.avatar_url = avatar_url
    db.session.commit()
    flash("Profile updated.", "success")
    return redirect(url_for("users.settings"))


def _replace_favorite_films(raw_ids: list[str]) -> None:
    tmdb_ids = []
    seen = set()
    for raw in raw_ids:
        raw = (raw or "").strip()
        if not raw:
            continue
        try:
            tmdb_id = int(raw)
        except ValueError as exc:
            raise ValueError("One favourite film is invalid.") from exc
        if tmdb_id in seen:
            continue
        seen.add(tmdb_id)
        tmdb_ids.append(tmdb_id)
        if len(tmdb_ids) == 4:
            break

    films = []
    for tmdb_id in tmdb_ids:
        try:
            film = ensure_film_cached(tmdb_id)
        except TMDBError as exc:
            raise ValueError("One favourite film could not be found.") from exc
        if film is None:
            raise ValueError("Film data is temporarily unavailable.")
        films.append(film)

    UserFavoriteFilm.query.filter_by(user_id=current_user.id).delete()
    db.session.flush()
    for index, film in enumerate(films):
        db.session.add(
            UserFavoriteFilm(
                user_id=current_user.id,
                film_id=film.tmdb_id,
                position=index,
            )
        )


def _handle_password_change():
    current = request.form.get("current_password", "")
    new = request.form.get("new_password", "")
    confirm = request.form.get("confirm_password", "")

    errors = []
    if not current_user.check_password(current):
        errors.append("Your current password is incorrect.")
    pw_err = password_error(new)
    if pw_err:
        errors.append(pw_err)
    if new != confirm:
        errors.append("New password and confirmation do not match.")

    if errors:
        for e in errors:
            flash(e, "error")
        return render_template("settings.html", user=current_user), 422

    current_user.set_password(new)
    db.session.commit()
    flash("Password changed.", "success")
    return redirect(url_for("users.settings"))


def _handle_letterboxd_import():
    token = request.form.get("import_token", "")
    path = _pending_import_path(token)
    if not token or path is None or not path.exists():
        flash("Preview your Letterboxd ZIP before importing.", "error")
        return redirect(url_for("users.settings") + "#import-settings")

    try:
        summary = import_letterboxd_bytes(path.read_bytes(), current_user)
    except LetterboxdImportError as exc:
        flash(str(exc), "error")
        return redirect(url_for("users.settings") + "#import-settings")
    finally:
        path.unlink(missing_ok=True)

    flash(
        "Imported Letterboxd data: "
        f"{summary.logs_added} logs added, "
        f"{summary.logs_updated} logs updated, "
        f"{summary.watchlist_added} watchlist items added"
        + (f", {summary.films_skipped} films skipped." if summary.films_skipped else "."),
        "success",
    )
    return redirect(url_for("users.settings") + "#import-settings")


def _handle_letterboxd_preview():
    export_file = request.files.get("letterboxd_export")
    if not export_file or not export_file.filename:
        flash("Choose your Letterboxd export ZIP.", "error")
        return redirect(url_for("users.settings") + "#import-settings")

    raw = export_file.read()
    try:
        preview = preview_letterboxd_zip(raw)
    except LetterboxdImportError as exc:
        flash(str(exc), "error")
        return redirect(url_for("users.settings") + "#import-settings")

    token = secrets.token_urlsafe(24)
    path = _pending_import_path(token, create=True)
    path.write_bytes(raw)
    return render_template(
        "settings.html",
        user=current_user,
        import_preview=preview,
        import_token=token,
    )


def _pending_import_path(token: str, create: bool = False) -> Path | None:
    if not token or any(ch in token for ch in ("/", "\\", ".")):
        return None
    folder = Path(Config.UPLOAD_DIR) / "imports"
    if create:
        folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{current_user.id}-{token}.zip"
