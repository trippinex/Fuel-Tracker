# Changelog

All notable changes to FuelTrack are documented here.

**Versioning scheme:**
- **Patch (1.0.X)** — bug fixes, small tweaks, security patches
- **Minor (1.X.0)** — new features, meaningful additions
- **Major (X.0.0)** — breaking changes, major redesigns

---

## [1.4.1] — 2026-05-25

- Fix: date inputs no longer overflow narrow containers on iOS Safari (Log Fill-Up screen, edit forms). Applies `min-width: 0; max-width: 100%` to all date / time input types.

---

## [1.4.0] — 2026-05-25 — Tailwind CSS production build

- Replaced Tailwind Play CDN with a pre-built, minified CSS file (~33 KB vs ~300 KB JS download per page)
- Eliminates the in-browser JIT compiler — no more flash of unstyled content on slow connections
- No more "do not use Play CDN in production" warning in the console
- Tightened CSP: removed `https://cdn.tailwindcss.com` from `script-src` and `style-src`
- Build pipeline:
  - `package.json` + `tailwind.config.js` with brand `fuel` colours and content scan paths
  - `app/static/css/tailwind.input.css` holds custom component classes (`.card`, `.btn-primary`, etc.)
  - `build_css.ps1` script rebuilds the CSS; output is committed so production needs no Node
- Updated `.gitignore` to skip `node_modules/` and `package-lock.json` (we commit the built CSS, not the build inputs)

---

## [1.3.0] — 2026-05-25 — Codebase optimization

**Security**
- Session cookies hardened: `Secure` (HTTPS-only), `HttpOnly` (no JS access), `SameSite=Lax` (CSRF defense)

**Maintainability — shared service modules**
- `app/services/mpg.py` — single source of truth for MPG / fleet-MPG calculation (was duplicated 3× across main, fillups, analytics)
- `app/services/photos.py` — single source of truth for photo upload validation (was duplicated 3× in vehicles routes)
- `app/services/ownership.py` — `get_owned_vehicle()` helper used across all routes for consistent authorization
- `app/templates/_icons.html` — reusable Jinja macros for common SVG icons

**Frontend**
- Extracted ~440 lines of inline JavaScript from `fillups_history.html` into `app/static/js/fillups_history.js` (faster page loads, browser-cacheable, easier to debug)

**Performance**
- Dashboard: replaced 3 aggregate SQL queries with in-memory sums over already-loaded data

**Future-proofing**
- Replaced deprecated `imghdr` (removed in Python 3.13) with inline magic-byte detector — no new dependency
- Replaced deprecated `datetime.utcnow()` with timezone-aware `datetime.now(timezone.utc)`

---

## [1.2.1] — 2026-05-25

- Login page: replaced SVG outline icon with the full app icon (fueltracker-192.png)

---

## [1.2.0] — 2026-05-25

- Fill-Up History: row-limit selector (5 / 10 / 15 / Max=25), default 10
- Fill-Up History: pagination controls (Previous / Page X of Y / Next)
- Pagination resets to page 1 on any filter change or row-limit change
- Previous disabled on first page; Next disabled on last page
- Pagination, filter, and row edit/delete all work together correctly

---

## [1.1.1] — 2026-05-25

- Dashboard recent fill-ups limited to 5 entries (was 10)

---

## [1.1.0] — 2026-05-25

- Added semantic versioning (`app/version.py`) as single source of truth
- Version badge (e.g. `v1.1.0`) now displayed in the Settings page
- Settings page includes a direct link to this changelog
- Added `CHANGELOG.md` to track changes per deployment
- Added `.gitattributes` to normalize line endings to LF across all platforms
- Source code published to GitHub: https://github.com/trippinex/Fuel-Tracker

---

## [1.0.0] — 2026-05-25 — Initial release

- Flask + SQLite fuel fill-up tracker, live at https://fueltracker.soccerwrek.net/
- Vehicle management with photo upload
- Fill-up logging (date, odometer, gallons, price per gallon)
- Analytics dashboard per vehicle: MPG trend, cost per mile, estimated range, Chart.js charts
- Full fill-up history with inline edit/delete (sticky headers, mobile cards)
- Google OAuth login with optional single-email allowlist
- Account settings with JSON backup/restore
- Progressive Web App (PWA) support with installable icons
- Security hardening: CSRF protection, HTTP security headers (CSP, HSTS, X-Frame-Options), safe redirects, analytics caching (300 s TTL), history capped at 500 rows
- Dashboard: fleet avg MPG summary cards, most-recent vehicle shown on mobile, vehicle count in section header
