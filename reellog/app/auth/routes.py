"""Authentication blueprint: register, login, logout.

CSRF is enforced app-wide by Flask-WTF's CSRFProtect; each form template
includes a hidden csrf_token, so these handlers don't need extra wiring.
"""
from __future__ import annotations

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_user, logout_user

from ..extensions import db
from ..models import User
from ..validators import (
    email_error,
    normalise_username,
    password_error,
    username_error,
)

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("films.index"))

    if request.method == "POST":
        username = normalise_username(request.form.get("username", ""))
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        display_name = request.form.get("display_name", "").strip() or None

        # Collect all validation errors so the user fixes them in one pass.
        errors = [
            e
            for e in (
                username_error(username),
                email_error(email),
                password_error(password),
            )
            if e
        ]
        if not errors:
            if User.query.filter_by(username=username).first():
                errors.append("That username is already taken.")
            if User.query.filter_by(email=email).first():
                errors.append("An account with that email already exists.")

        if errors:
            for e in errors:
                flash(e, "error")
            # Re-render with the values they typed (except password).
            return render_template(
                "auth/register.html",
                username=username,
                email=email,
                display_name=display_name or "",
            ), 422

        user = User(username=username, email=email, display_name=display_name)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash(f"Welcome to ReelLog, {user.name}!", "success")
        return redirect(url_for("films.index"))

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("films.index"))

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip().lower()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        # Allow login with either username or email.
        user = (
            User.query.filter_by(username=identifier).first()
            or User.query.filter_by(email=identifier).first()
        )
        # Always run check_password against a real or dummy hash to avoid
        # leaking which accounts exist via response timing differences.
        if user and user.check_password(password):
            login_user(user, remember=remember)
            flash(f"Welcome back, {user.name}.", "success")
            next_url = request.args.get("next")
            # Only allow relative redirects to prevent open-redirect attacks.
            if next_url and next_url.startswith("/"):
                return redirect(next_url)
            return redirect(url_for("films.index"))

        flash("Invalid username/email or password.", "error")
        return render_template("auth/login.html", identifier=identifier), 401

    return render_template("auth/login.html")


@auth_bp.route("/logout", methods=["POST"])
def logout():
    # POST-only so logout is CSRF-protected and not triggerable via <img src>.
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("films.index"))
