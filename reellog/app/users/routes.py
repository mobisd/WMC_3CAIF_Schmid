"""Users blueprint: public profiles, diary, watchlist, and settings.

The /<username> route is a catch-all, so this blueprint is registered LAST in
the app factory. Reserved usernames (api, film, ...) can never be created, so
they can never shadow real routes here.
"""
from __future__ import annotations

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
from ..models import FavoriteFilm, Film, LogEntry, User, WatchlistItem
from ..uploads import UploadError, delete_upload, save_image
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
    # Eager-load films for the activity cards (avoid N+1).
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

    favorites = (
        FavoriteFilm.query.options(joinedload(FavoriteFilm.film))
        .filter_by(user_id=user.id)
        .order_by(FavoriteFilm.position.asc())
        .all()
    )

    # Sidebar previews.
    watchlist_preview = (
        WatchlistItem.query.options(joinedload(WatchlistItem.film))
        .filter_by(user_id=user.id)
        .order_by(WatchlistItem.added_at.desc())
        .limit(5)
        .all()
    )
    diary_preview = (
        LogEntry.query.options(joinedload(LogEntry.film))
        .filter(LogEntry.user_id == user.id, LogEntry.watched_on.isnot(None))
        .order_by(LogEntry.watched_on.desc(), LogEntry.created_at.desc())
        .limit(6)
        .all()
    )

    # Ratings histogram: counts of ratings 1..10 (½..5 stars) across all logs.
    histogram = [0] * 10
    for log in user.logs:
        if log.rating:
            histogram[log.rating - 1] += 1

    return render_template(
        "profile.html",
        user=user,
        recent_logs=recent_logs,
        reviews=reviews,
        favorites=favorites,
        watchlist_preview=watchlist_preview,
        diary_preview=diary_preview,
        histogram=histogram,
        max_favorites=Config.MAX_FAVORITE_FILMS,
    )


@users_bp.route("/<username>/films")
def films(username: str):
    user = _get_user_or_404(username)
    # All distinct films the user has logged, most-recently-logged first.
    logs = (
        LogEntry.query.options(joinedload(LogEntry.film))
        .filter_by(user_id=user.id)
        .order_by(LogEntry.created_at.desc())
        .all()
    )
    seen: set[int] = set()
    films = []
    for log in logs:
        if log.film_id not in seen:
            seen.add(log.film_id)
            films.append(log.film)
    return render_template("films.html", user=user, films=films)


@users_bp.route("/<username>/diary")
def diary(username: str):
    user = _get_user_or_404(username)
    logs = (
        LogEntry.query.options(joinedload(LogEntry.film))
        .filter_by(user_id=user.id)
        # Order by watched date when present, else by creation; newest first.
        .order_by(
            LogEntry.watched_on.desc().nullslast(),
            LogEntry.created_at.desc(),
        )
        .all()
    )
    return render_template("diary.html", user=user, logs=logs)


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


@users_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    if request.method == "POST":
        form_type = request.form.get("form_type", "profile")

        if form_type == "password":
            return _handle_password_change()
        return _handle_profile_update()

    return render_template(
        "settings.html", user=current_user, backdrop_films=_backdrop_picker_films()
    )


def _backdrop_picker_films():
    logged = (
        Film.query.join(LogEntry, LogEntry.film_id == Film.tmdb_id)
        .filter(LogEntry.user_id == current_user.id, Film.backdrop_path.isnot(None))
        .all()
    )
    watchlisted = (
        Film.query.join(WatchlistItem, WatchlistItem.film_id == Film.tmdb_id)
        .filter(WatchlistItem.user_id == current_user.id, Film.backdrop_path.isnot(None))
        .all()
    )
    films = {}
    for film in [*logged, *watchlisted]:
        films.setdefault(film.tmdb_id, film)
    return list(films.values())


def _resolve_image_field(field: str, label: str, current, errors: list):
    """Work out the new value for avatar_url / backdrop_url from the form.

    Precedence: an explicit "remove" checkbox wins, then an uploaded file,
    then a pasted URL; otherwise the current value is kept. Old uploads are
    cleaned up when replaced/removed. Validation errors are appended to
    ``errors`` and the current value is preserved.
    """
    if request.form.get(f"remove_{field}"):
        delete_upload(current)
        return None

    uploaded = request.files.get(f"{field}_file")
    if uploaded and uploaded.filename:
        try:
            new_url = save_image(uploaded, field)
        except UploadError as exc:
            errors.append(f"{label}: {exc}")
            return current
        delete_upload(current)
        return new_url

    pasted = request.form.get(f"{field}_url", "").strip()
    if pasted:
        err = url_error(pasted, Config.URL_MAX_LEN)
        if err:
            errors.append(f"{label} {err}")
            return current
        if current != pasted:
            delete_upload(current)
        return pasted

    return current


def _handle_profile_update():
    display_name = request.form.get("display_name", "").strip() or None
    bio = request.form.get("bio", "").strip() or None
    backdrop_films = _backdrop_picker_films()
    backdrop_choices = {film.tmdb_id: film for film in backdrop_films}

    errors = []
    if bio and len(bio) > Config.BIO_MAX_LEN:
        errors.append(f"Bio is too long (max {Config.BIO_MAX_LEN} characters).")
    if display_name and len(display_name) > 80:
        errors.append("Display name is too long (max 80 characters).")

    new_avatar = _resolve_image_field("avatar", "Avatar", current_user.avatar_url, errors)
    new_backdrop = current_user.backdrop_url
    if request.form.get("remove_backdrop"):
        delete_upload(current_user.backdrop_url)
        new_backdrop = None
    else:
        backdrop_film_id = request.form.get("backdrop_film_id", "").strip()
        if backdrop_film_id:
            try:
                backdrop_film_id_int = int(backdrop_film_id)
            except ValueError:
                errors.append("Choose a valid film backdrop.")
            else:
                film = backdrop_choices.get(backdrop_film_id_int)
                if not film:
                    errors.append("Choose a valid film backdrop.")
                else:
                    delete_upload(current_user.backdrop_url)
                    new_backdrop = film.backdrop_url("w1280")

    if errors:
        for e in errors:
            flash(e, "error")
        return (
            render_template(
                "settings.html",
                user=current_user,
                backdrop_films=backdrop_films,
            ),
            422,
        )

    current_user.display_name = display_name
    current_user.bio = bio
    current_user.avatar_url = new_avatar
    current_user.backdrop_url = new_backdrop
    db.session.commit()
    flash("Profile updated.", "success")
    return redirect(url_for("users.settings"))


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
