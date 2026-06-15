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
