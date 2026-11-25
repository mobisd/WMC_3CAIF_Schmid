"""People blueprint: a page per cast member / director.

Mirrors the films blueprint's graceful-degradation contract: a bad id is a
clean 404, a TMDB outage falls back to cached identity + an empty filmography,
never a 500.
"""
from __future__ import annotations

from flask import Blueprint, abort, render_template
from flask_login import current_user

from ..tmdb import TMDBError, get_person

people_bp = Blueprint("people", __name__)


@people_bp.route("/person/<int:tmdb_id>")
def person(tmdb_id: int):
    try:
        person_obj, filmography = get_person(tmdb_id)
    except TMDBError:
        abort(404)
    if person_obj is None:
        # TMDB unreachable and nothing cached.
        abort(404)

    # "You've watched X of Y" — only for the logged-in user, computed by
    # intersecting their logged film ids with this filmography.
    watched_count = 0
    total = len(filmography)
    if current_user.is_authenticated and filmography:
        film_ids = {f["tmdb_id"] for f in filmography}
        watched_count = len(
            {log.film_id for log in current_user.logs if log.film_id in film_ids}
        )

    return render_template(
        "person.html",
        person=person_obj,
        filmography=filmography,
        watched_count=watched_count,
        total=total,
    )
