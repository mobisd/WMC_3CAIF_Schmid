"""Application factory."""
from __future__ import annotations

import click
from flask import Flask, render_template, send_from_directory

from .config import Config
from .extensions import csrf, db, login_manager


def create_app(config_class: type = Config) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from . import models  # noqa: F401
    with app.app_context():
        db.create_all()

    from .api.routes import api_bp
    from .auth.routes import auth_bp
    from .films.routes import films_bp
    from .people.routes import people_bp
    from .users.routes import users_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(films_bp)
    app.register_blueprint(people_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(users_bp)

    @app.route("/uploads/<path:filename>")
    def uploads(filename):
        return send_from_directory(app.config["UPLOAD_DIR"], filename)

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
    from .images import effective_backdrop_url, effective_poster_url

    @app.context_processor
    def inject_globals():
        today = date.today()
        return {
            "current_year": today.year,
            "today_iso": today.isoformat(),
            "effective_poster_url": effective_poster_url,
            "effective_backdrop_url": effective_backdrop_url,
        }
