# ReelLog

A self-hosted Letterboxd-style film diary for school. Users search films via
TMDB, keep a diary, rate in half-star steps, write reviews, build a watchlist,
and customise profile and film images.

## Features

- Account register, login, and logout with hashed passwords and CSRF.
- Film search and film pages with poster, backdrop, cast, synopsis, runtime,
  director, and TMDB rating.
- One-entry-per-watch logging: quick rating, like, and review actions upsert the
  current diary entry. Only explicit "Log again" creates a rewatch row.
- Profile backdrops are film-sourced through a TMDB film search and backdrop
  picker. The TMDB key stays server-side.
- Profile avatars can be uploaded from disk or provided as an image URL.
- The nav search includes both films and accounts.
- Per-user film poster/backdrop overrides via the film page. A user's chosen
  images display on the film page, activity grids, watchlist, diary thumbs, and
  cached search results.
- Watchlist add/remove.

## Setup

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Set `SECRET_KEY` and `TMDB_API_KEY` in `.env`.

Create missing tables:

```bash
flask --app run init-db
```

`init-db` imports all models before `db.create_all()`, so fresh databases create
`user_film_images` along with the existing user, film, watchlist, and log
tables. Existing SQLite databases should re-run `init-db` after pulling these
changes.

Run:

```bash
flask --app run run --debug
```

Open <http://127.0.0.1:5000>.

## Tailwind

Rebuild CSS after changing templates, JS class names, or Tailwind config:

```bash
npx --yes tailwindcss@3.4.17 -c tailwind.config.js -i app/static/css/input.css -o app/static/css/output.css --minify
```

The committed `app/static/css/output.css` is used when `TAILWIND_CDN=0`.

## Tests

```bash
python -m pytest -q
```

The focused tests cover:

- `UserFilmImage` override set/reset and per-user ownership.
- Effective image helper fallback vs override behavior.
- Profile backdrop save/remove through the server-side TMDB image path.
- Logging upsert behavior for a newly logged film, with explicit rewatch as the
  only second-row path.

## Notes

- TMDB API keys are never exposed to the browser. The app uses local JSON
  endpoints for search, image lists, backdrop saves, and per-film overrides.
- Old duplicate diary rows are pre-fix data. Delete them manually or reset the
  local database if you want a clean diary history.
- Profile banner framing is intentionally full-bleed, taller, and centered so
  chosen backdrops behave more like Letterboxd banners.
