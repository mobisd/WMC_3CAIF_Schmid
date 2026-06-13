# ReelLog 🎬

A self-hosted, **Letterboxd-style film diary** for a school. Users search films
(via TMDB), keep a watch diary, rate films in ½–5 stars, write reviews, build a
watchlist, and customise a public profile.

Built with Flask (app-factory + blueprints), SQLite via Flask-SQLAlchemy,
Flask-Login, Flask-WTF (CSRF), vanilla JS (ES modules), and Tailwind CSS.

---

## Features

- Account register / login / logout (hashed passwords, CSRF on every form).
- Film search + a full page per film (backdrop, poster, cast, synopsis,
  director, runtime, TMDB rating). The backdrop fades smoothly into the page
  and the poster overlaps it in a centred three-column layout.
- **Clickable cast & director** → a **person page** (`/person/<id>`) showing
  that person's filmography, photo, bio, a TMDB link, and a “you've watched
  X of Y” progress stat. People are cached locally like films.
- Watchlist add/remove (idempotent toggle).
- Mark watched, rate (½–5 stars, half-star increments), log with a date,
  rewatch flag, like, and write reviews (with optional spoiler flag).
- **Favourite four**: pin up to 4 films to your profile (favourite from any
  film page; remove from your own profile).
- Public profiles: faded backdrop banner + avatar, stats strip, favourites,
  recent activity (with rating/like overlays), reviews, plus a sidebar with a
  watchlist preview, diary list and a ratings histogram. Tabs: Activity ·
  Films · Diary · Reviews · Watchlist.
- Per-account customisation via **Edit profile**: display name, bio, and
  **uploaded** avatar / backdrop images (or paste a URL). You can also set your
  profile backdrop straight from any film page.
- All TMDB calls are proxied server-side; films and people are cached locally
  in SQLite. Uploaded images live under `instance/uploads/` (gitignored).

---

## Prerequisites

- **Python 3.11+**
- A free **TMDB API key** (v3): create an account at
  <https://www.themoviedb.org/>, then go to **Settings → API** and request a
  developer key. Copy the **API Key (v3 auth)** value.
- *(Optional)* the **standalone Tailwind CLI** if you want to rebuild the CSS
  (a pre-built `app/static/css/output.css` is already committed, so you can run
  the app without it).

---

## Setup

All commands are run from the `reellog/` directory. They work on
Linux / macOS / Windows (PowerShell variations noted).

### 1. Create and activate a virtual environment

```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env      # Windows: copy .env.example .env
```

Edit `.env` and set:

- `SECRET_KEY` — a long random string. Generate one with:
  ```bash
  python -c "import secrets; print(secrets.token_hex(32))"
  ```
- `TMDB_API_KEY` — your TMDB v3 API key.

The app **refuses to start** with a clear error if either is missing.

### 4. Initialise the database

```bash
flask --app run init-db
```

This creates `instance/app.db` with all tables. It is idempotent and never
drops data — **re-run it after pulling** so the newer `people` and
`favorite_films` tables are created (it only adds missing tables).

Uploaded avatars/backdrops are written to `instance/uploads/` (created on
first upload). The whole `instance/` folder is gitignored.

### 5. Run the app

```bash
flask --app run run --debug
# or simply:
python run.py
```

Open <http://127.0.0.1:5000>.

---

## Tailwind CSS

A minified `app/static/css/output.css` is **committed**, so the app is fully
styled out of the box (the default `TAILWIND_CDN=0` makes `base.html` load it).

### Rebuilding the CSS (only if you change templates/classes)

1. Download the standalone Tailwind CLI (no Node project needed) from the
   [Tailwind releases page](https://github.com/tailwindlabs/tailwindcss/releases),
   pick the binary for your OS, e.g. on Linux:
   ```bash
   curl -sLo tailwindcss https://github.com/tailwindlabs/tailwindcss/releases/download/v3.4.17/tailwindcss-linux-x64
   chmod +x tailwindcss
   ```
   (Or use `npx tailwindcss …` if you prefer Node.)
2. Build once:
   ```bash
   ./tailwindcss -c tailwind.config.js -i app/static/css/input.css -o app/static/css/output.css --minify
   ```
3. Or watch during development:
   ```bash
   ./tailwindcss -c tailwind.config.js -i app/static/css/input.css -o app/static/css/output.css --watch
   ```

### First-run-only CDN alternative

If you'd rather not deal with the CLI while iterating, set `TAILWIND_CDN=1` in
`.env`. `base.html` will then load the **Tailwind Play CDN** plus
`cdn-extras.css` (plain-CSS versions of our component classes). **Do not ship
the CDN to production** — build `output.css` and leave `TAILWIND_CDN=0`.

---

## Tests

A small pytest suite covers the key routes and the security-sensitive bits
(person page with TMDB mocked, upload validation — oversized / wrong type /
path-traversal filenames, the favourite-films cap, and profile actions). It
runs against an in-memory SQLite DB and stubs out all network calls, so no
TMDB key is needed.

```bash
pip install pytest
pytest -q
```

---

## Production hardening notes

This project targets a small school deployment. Before exposing it publicly:

- Serve over **HTTPS** and set `SESSION_COOKIE_SECURE=1` in the environment.
- Run behind a real WSGI server (e.g. `gunicorn 'run:app'`) — **not**
  `flask run` / `debug=True`.
- Set a strong, secret `SECRET_KEY`; never commit `.env`.
- Set `TAILWIND_CDN=0` and ship the built `output.css` (no external CDN).
- Put the app behind a reverse proxy (nginx) and consider rate-limiting auth
  endpoints.
- Back up `instance/app.db` regularly.

---

## Project layout

```
reellog/
├── app/
│   ├── __init__.py      # create_app() factory, CLI, error handlers
│   ├── config.py        # env-driven config (fails fast on missing secrets)
│   ├── extensions.py    # db, login_manager, csrf singletons
│   ├── models.py        # User, Film, Person, WatchlistItem, LogEntry, FavoriteFilm
│   ├── tmdb.py          # server-side TMDB client + caching + fallbacks
│   ├── uploads.py       # avatar/backdrop image validation + processing (Pillow)
│   ├── validators.py    # username/email/url/rating/date validation
│   ├── auth/ films/ people/ users/ api/   # blueprints
│   ├── templates/       # Jinja templates (base, partials, pages, errors)
│   └── static/          # css (input/output), js (api/main/search/film/profile), img
├── instance/            # app.db + uploads/ live here (gitignored)
├── requirements.txt  .env.example  .gitignore  tailwind.config.js  run.py
└── README.md
```

### Key design decisions

- **Ratings stored as integers 1–10** (each = half a star). Converted to
  0.5–5.0 only at the display/input edge — no float precision bugs.
- **A film is "watched"** iff ≥1 `LogEntry` exists; **current rating** = the
  most recent rated log. "Mark watched" / quick-rate create a dated `LogEntry`.
- **Films are cached locally** so foreign keys are stable and we don't hammer
  TMDB; entries refresh after 7 days. TMDB outages/404/429 degrade gracefully
  (serve cache, friendly 404, empty states) — never a 500 stack trace.
- **CSRF everywhere**: forms include a hidden token; JS `fetch` sends it via the
  `X-CSRFToken` header (read from a `<meta>` tag) — see `static/js/api.js`.
- **No `innerHTML` with raw data**: the live-search dropdown builds nodes with
  `textContent`, so external titles can't inject markup. Jinja autoescaping
  covers server-rendered user content.
- **Reserved usernames** (`api`, `film`, `search`, `settings`, …) can't be
  registered, so they never shadow the catch-all `/<username>` route.

---

## Known limitations

- "Today" uses the **server's** local date for the future-date check; there's
  no per-user timezone handling (kept intentionally simple).
- Search exposes page-based pagination (Previous/Next), not infinite scroll.
- The quick-rate widget on the film page always creates a **new** dated diary
  entry; to change or clear a rating, edit/delete a specific entry.
- No email verification or password reset flow.
- TMDB image sizes are fixed per context (no responsive `srcset`).

## Next features (nice-to-haves)

1. **Lists** — user-curated film lists (ranked or unranked), public/private.
2. **Following / friends activity feed** — see what classmates logged recently.
3. **Likes & comments on reviews** — lightweight social interaction.
4. **Year-in-review stats** — films/hours watched, top directors, rating
   distribution.
```
