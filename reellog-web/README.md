# ReelLog — a film diary (no backend)

A professional, minimalist **Letterboxd-style film diary** built as a single
self-contained web page. **No Python, no server, no build step, no API key.**
Browse films, rate them in half-stars, write reviews, keep a diary and a
watchlist — everything saved locally in your browser.

Designed in an Apple idiom: the system **San Francisco** font (SF Pro on a Mac),
a calm cinematic dark palette, translucent blurred navigation, and smooth
spring-based motion.

## Run it

Just open the file — there is nothing to install.

- **macOS:** double-click `index.html` (or run `open index.html` in this folder).
  Because the app uses the system font stack, you get real **SF Pro** on a Mac.
- Any OS: drag `index.html` onto a browser window.

Optional, if you prefer a local server (not required):

```bash
cd reellog-web
python3 -m http.server 8000   # then visit http://localhost:8000
```

## What's inside

- `index.html` — the entire app: HTML, CSS and vanilla JavaScript in one file,
  plus a bundled catalogue of 48 notable films. That's it.

## Features

- **Browse & search** the catalogue by title, director or genre (live filter).
- **Film pages** with a backdrop hero, generated poster art, cast and synopsis.
- **Rate** in ½–5 stars with a keyboard-accessible hover widget.
- **Log** watches with a date, **review** (with spoiler flag), **like**, rewatch.
- **Diary**, **Watchlist**, and a **Profile** with stats, favourites (up to 4)
  and a ratings histogram.
- Edit/delete any diary entry; delete has an **Undo**.
- Works offline and respects `prefers-reduced-motion`.

## Notes & decisions

- **No TMDB / API key.** A static site can't hide a key, so instead of calling
  an external API, the catalogue is bundled and poster/backdrop artwork is
  **generated** from each film's id (a deterministic duotone). Nothing loads
  from the network, so nothing can break or leak.
- **Storage is per-device.** Your diary, ratings and watchlist live in this
  browser's `localStorage` under the key `reellog.v1`. There are no accounts;
  clearing site data resets it. Every read/write is wrapped in try/catch so the
  app still runs in private mode.
- **Routing** uses the URL hash (`#home`, `#browse`, `#diary`, `#watchlist`,
  `#profile`, `#film-<id>`) so Back/Forward and sharing within the app work.

## Possible next steps

1. Import real posters by letting the user paste their own TMDB key (stored
   locally) and swapping the generated art for `image.tmdb.org` URLs.
2. Export / import the diary as a JSON file for backup or moving devices.
3. Custom **lists** (ranked or themed) beyond the single watchlist.
4. A "year in review" stats page (hours watched, top directors).
