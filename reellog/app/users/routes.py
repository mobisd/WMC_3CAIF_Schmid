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
from ..models import LogEntry, User, WatchlistItem
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
            .limit(10)
            .all()
        )
        if log.has_review
    ]
    return render_template(
        "profile.html", user=user, recent_logs=recent_logs, reviews=reviews
    )


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

    return render_template("settings.html", user=current_user)


def _handle_profile_update():
    display_name = request.form.get("display_name", "").strip() or None
    bio = request.form.get("bio", "").strip() or None
    avatar_url = request.form.get("avatar_url", "").strip() or None
    backdrop_url = request.form.get("backdrop_url", "").strip() or None

    errors = []
    if bio and len(bio) > Config.BIO_MAX_LEN:
        errors.append(f"Bio is too long (max {Config.BIO_MAX_LEN} characters).")
    if display_name and len(display_name) > 80:
        errors.append("Display name is too long (max 80 characters).")
    for label, value in (("Avatar", avatar_url), ("Backdrop", backdrop_url)):
        err = url_error(value or "", Config.URL_MAX_LEN)
        if err:
            errors.append(f"{label} {err}")

    if errors:
        for e in errors:
            flash(e, "error")
        return render_template("settings.html", user=current_user), 422

    current_user.display_name = display_name
    current_user.bio = bio
    current_user.avatar_url = avatar_url
    current_user.backdrop_url = backdrop_url
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
