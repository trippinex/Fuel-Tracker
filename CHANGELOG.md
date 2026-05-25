# Changelog

All notable changes to FuelTrack are documented here.  
Format: `[YYYY-MM-DD] — Summary` followed by a bullet list of changes.

---

## [2026-05-25] — Initial GitHub release

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
