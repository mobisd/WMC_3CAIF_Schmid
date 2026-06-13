"""Application factory.

Creating the app inside a function keeps config/extensions from binding at
import time, which makes testing and multiple instances clean.
"""
from __future__ import annotations

import click
from flask import Flask, render_template

from .config import Config
from .extensions import csrf, db, login_manager


def create_app(config_class: type = Config) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    # Initialise extensions.
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Import models so SQLAlchemy + the user_loader are registered.
    from . import models  # noqa: F401

    # Register blueprints.
    from .api.routes import api_bp
    from .auth.routes import auth_bp
    from .films.routes import films_bp
    from .users.routes import users_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(films_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    # users_bp last: it owns the catch-all /<username> route, so more specific
    # routes (login, search, film, ...) must be registered before it.
    app.register_blueprint(users_bp)

    _register_error_handlers(app)
    _register_cli(app)
    _register_template_globals(app)

    return app


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(404)
    def not_found(_err):
        return render_template("errors/404.html"), 404

    @app.errorhandler(403)
    def forbidden(_err):
        return render_template("errors/403.html"), 403

    @app.errorhandler(500)
    def server_error(_err):
        return render_template("errors/500.html"), 500


def _register_cli(app: Flask) -> None:
    @app.cli.command("init-db")
    def init_db():
        """Create all database tables (idempotent; never drops data)."""
        db.create_all()
        click.echo("Initialised the database (tables created if missing).")


def _register_template_globals(app: Flask) -> None:
    from datetime import date

    @app.context_processor
    def inject_globals():
        # Used by templates for the footer year and 'today' max on date inputs.
        today = date.today()
        return {"current_year": today.year, "today_iso": today.isoformat()}
