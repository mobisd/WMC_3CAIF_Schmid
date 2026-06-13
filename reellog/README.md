# ReelLog

A self-hosted, Letterboxd-style film diary for a school. Users search films via
TMDB, keep a watch diary, rate films in half-star steps, write reviews, build a
watchlist, and customise a public profile.

Built with Flask, SQLite via Flask-SQLAlchemy, Flask-Login, Flask-WTF CSRF,
vanilla JS modules, and Tailwind CSS.

## Features

- Account register, login, and logout with hashed passwords and CSRF.
- Film search and film pages with backdrop, poster, cast, synopsis, director,
  runtime, and TMDB rating.
- Person pages for cast and directors, cached locally like films.
- Watchlist toggle and favourite-four profile pins.
- One-entry-per-watch logging: quick rating, like, review, and mark-watched
  actions update the user's current entry for that film. Explicit "Log again"
  creates a new `is_rewatch=True` diary entry.
- Public profiles with film-sourced backdrops, avatar, stats, favourites,
  activity, reviews, watchlist preview, diary preview, and ratings histogram.
- Settings for display name, bio, uploaded avatar, and a backdrop chosen from
  films the user has logged or watchlisted. Film pages can also set the profile
  backdrop.
- TMDB keys stay server-side. Films and people are cached locally in SQLite.

## Setup

All commands run from the `reellog/` directory.

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows PowerShell
pip install -r requirements.txt
copy .env.example .env
```

Set `SECRET_KEY` and `TMDB_API_KEY` in `.env`. The app refuses to start if
either is missing.

Initialise the database:

```bash
flask --app run init-db
```

The command imports all models before `db.create_all()`, so fresh clones create
the `users`, `films`, `people`, `watchlist_items`, `favorite_films`, and
`log_entries` tables. It is idempotent and never drops data.

Run the app:

```bash
flask --app run run --debug
# or
python run.py
```

Open <http://127.0.0.1:5000>.

Uploaded avatars are written to `instance/uploads/`, which is gitignored.
Profile backdrops are TMDB film backdrop URLs, not local uploads.

## Tailwind CSS

The committed `app/static/css/output.css` is used by default.

Rebuild after changing templates, JS classes, or Tailwind tokens:

```bash
npx tailwindcss -c tailwind.config.js -i app/static/css/input.css -o app/static/css/output.css --minify
```

You can also use the standalone Tailwind CLI. During local first-run iteration,
`TAILWIND_CDN=1` enables the Tailwind Play CDN plus `cdn-extras.css`; do not use
the CDN for production.

## Tests

The pytest suite uses an in-memory SQLite database and mocks network-sensitive
paths where needed.

```bash
pytest -q
```

Coverage includes page smoke tests, person pages, avatar upload validation,
favourite limits, profile backdrop actions, and logging semantics:

- Rate, like, and review the same film without rewatching creates exactly one
  `LogEntry`.
- Editing rating or review keeps one row and updates its values.
- Explicit rewatch creates a second diary row ordered newest first.

## Logging Rules

- A film is watched when at least one `LogEntry` exists for `(user, film)`.
- The current entry is the user's most recent `LogEntry` for that film.
- Quick/default actions upsert the current entry.
- Clearing a rating sets `rating = NULL` while keeping the entry.
- Only the explicit "Log again" / rewatch path inserts another row.
- Older development databases may already contain duplicate rows; delete those
  manually or reset the local database if you want clean diary history.

## Project Layout

```text
reellog/
  app/
    __init__.py      # app factory, CLI, error handlers
    config.py        # env-driven config
    extensions.py    # db, login_manager, csrf
    models.py        # User, Film, Person, WatchlistItem, LogEntry, FavoriteFilm
    tmdb.py          # server-side TMDB client and caching
    uploads.py       # avatar image validation and processing
    validators.py    # username, email, url, rating, date validation
    auth/ films/ people/ users/ api/
    templates/
    static/
  instance/          # app.db and uploads, gitignored
  requirements.txt
  tailwind.config.js
  run.py
```

## Production Notes

- Serve over HTTPS and set secure cookie options.
- Run behind a real WSGI server, not the Flask debug server.
- Keep `SECRET_KEY` and `TMDB_API_KEY` out of git.
- Build and commit `output.css` with `TAILWIND_CDN=0`.
- Back up `instance/app.db` regularly.
