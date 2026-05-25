# Changelog

All notable changes to FuelTrack are documented here.

**Versioning scheme:**
- **Patch (1.0.X)** — bug fixes, small tweaks, security patches
- **Minor (1.X.0)** — new features, meaningful additions
- **Major (X.0.0)** — breaking changes, major redesigns

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
