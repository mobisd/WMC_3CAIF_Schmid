"""Personen-Seiten: Daten und Film-Credits kommen aus TMDB."""
from __future__ import annotations

from flask import Blueprint, abort, render_template

from ..tmdb import TMDBError, get_person, get_person_movie_credits

people_bp = Blueprint("people", __name__, url_prefix="/people")


@people_bp.route("/<int:person_id>")
def person(person_id: int):
    # Einzelne Person laden und darunter bekannte Filme anzeigen.
    try:
        person_data = get_person(person_id)
    except TMDBError:
        abort(404)
    if person_data is None:
        abort(404)

    credits = get_person_movie_credits(person_id)
    return render_template("person.html", person=person_data, credits=credits)
