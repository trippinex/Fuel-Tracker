import os

from flask import Flask
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix

from .database import db
from .version import __version__

csrf = CSRFProtect()


def create_app():
    app = Flask(__name__)

    db_path = os.environ.get('DATABASE_PATH', os.path.join(os.getcwd(), 'fuel_tracker.db'))
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    _secret_key = os.environ.get('SECRET_KEY', '')
    _dev_default = 'dev-secret-key-change-in-production'
    if not _secret_key or _secret_key == _dev_default:
        raise RuntimeError(
            'SECRET_KEY environment variable is missing or set to the insecure default. '
            'Generate a strong key with:\n'
            '  python -c "import secrets; print(secrets.token_hex(32))"'
        )
    app.config['SECRET_KEY'] = _secret_key
    app.config['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID', '')
    app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET', '')

    # ── Session cookie security ──────────────────────────────────────────
    # SECURE   — only sent over HTTPS (production has TLS via nginx).
    # HTTPONLY — not readable from JavaScript, mitigating XSS cookie theft.
    # SAMESITE — 'Lax' blocks CSRF on most cross-site requests while still
    #            allowing top-level navigation (required for OAuth redirect).
    app.config['SESSION_COOKIE_SECURE']   = not app.debug
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    photos_path = os.environ.get('PHOTOS_PATH', '/var/lib/fueltrack/photos')
    os.makedirs(photos_path, exist_ok=True)
    app.config['PHOTOS_PATH'] = photos_path

    # Trust X-Forwarded-Proto from nginx so url_for generates https:// URIs
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    db.init_app(app)
    csrf.init_app(app)

    # ── Flask-Login ──────────────────────────────────────────────────────────
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please sign in to continue.'
    login_manager.login_message_category = 'error'

    @login_manager.user_loader
    def load_user(user_id):
        from .models import User
        return db.session.get(User, int(user_id))

    # ── Database ─────────────────────────────────────────────────────────────
    with app.app_context():
        from . import models  # noqa: F401 — must import before create_all
        db.create_all()

        # Inline migrations: add columns / indexes if they don't exist
        for ddl in [
            'ALTER TABLE vehicles ADD COLUMN user_id INTEGER REFERENCES users(id)',
            'ALTER TABLE vehicles ADD COLUMN vin TEXT',
            'ALTER TABLE vehicles ADD COLUMN license_plate TEXT',
            'ALTER TABLE vehicles ADD COLUMN photo_filename TEXT',
            'CREATE INDEX IF NOT EXISTS ix_vehicles_user_id ON vehicles(user_id)',
            'CREATE INDEX IF NOT EXISTS ix_fill_ups_vehicle_id ON fill_ups(vehicle_id)',
            'CREATE INDEX IF NOT EXISTS ix_fill_ups_date ON fill_ups(date)',
        ]:
            try:
                with db.engine.connect() as conn:
                    conn.execute(db.text(ddl))
                    conn.commit()
            except Exception:
                pass  # Column already exists — that's fine

    # ── Blueprints ───────────────────────────────────────────────────────────
    from .routes.main import main_bp
    from .routes.vehicles import vehicles_bp
    from .routes.fillups import fillups_bp
    from .routes.analytics import analytics_bp
    from .routes.auth import auth_bp, init_oauth
    from .routes.settings import settings_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(vehicles_bp, url_prefix='/vehicles')
    app.register_blueprint(fillups_bp, url_prefix='/fillups')
    app.register_blueprint(analytics_bp, url_prefix='/analytics')
    app.register_blueprint(auth_bp)
    app.register_blueprint(settings_bp)

    # Exempt JSON-only AJAX endpoints from CSRF — they have no form to carry
    # a token and are already guarded by @login_required.
    csrf.exempt(app.view_functions['fillups.edit_fillup'])
    csrf.exempt(app.view_functions['fillups.delete_fillup'])

    # Initialize the analytics cache (SimpleCache, TTL 300 s)
    from .routes.analytics import cache as analytics_cache
    analytics_cache.init_app(app)

    init_oauth(app)

    # ── Template context — version available in every template ────────────
    @app.context_processor
    def inject_version():
        return {'app_version': __version__}

    # ── HTTP security headers ─────────────────────────────────────────────
    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), camera=(), microphone=()'
        if not app.debug:
            response.headers['Strict-Transport-Security'] = (
                'max-age=31536000; includeSubDomains'
            )
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https://lh3.googleusercontent.com; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "object-src 'none'; "
            "base-uri 'self';"
        )
        response.headers['Content-Security-Policy'] = csp
        return response

    return app
