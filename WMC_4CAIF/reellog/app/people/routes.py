"""Actor/person pages backed by TMDB."""
from __future__ import annotations

from flask import Blueprint, abort, render_template

from ..tmdb import TMDBError, get_person, get_person_movie_credits

people_bp = Blueprint("people", __name__, url_prefix="/people")


@people_bp.route("/<int:person_id>")
def person(person_id: int):
    try:
        person_data = get_person(person_id)
    except TMDBError:
        abort(404)
    if person_data is None:
        abort(404)

    credits = get_person_movie_credits(person_id)
    return render_template("person.html", person=person_data, credits=credits)
