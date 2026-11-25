"""Flask extension singletons.

Kept in their own module (not __init__.py) to avoid circular imports: models
and blueprints import `db` / `login_manager` from here, while the app factory
imports this module and calls each extension's init_app().
"""
from __future__ import annotations

from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()

# Where @login_required redirects anonymous users, and the flash category.
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to continue."
login_manager.login_message_category = "info"
