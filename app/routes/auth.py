import os

from flask import Blueprint, redirect, url_for, render_template, flash
from flask_login import login_user, logout_user, login_required, current_user
from authlib.integrations.flask_client import OAuth

from ..models import User, Vehicle
from ..database import db

auth_bp = Blueprint('auth', __name__)
oauth = OAuth()


def init_oauth(app):
    oauth.init_app(app)
    oauth.register(
        name='google',
        client_id=app.config['GOOGLE_CLIENT_ID'],
        client_secret=app.config['GOOGLE_CLIENT_SECRET'],
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'},
    )


@auth_bp.route('/login')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    return render_template('login.html')


@auth_bp.route('/auth/google')
def google_login():
    redirect_uri = url_for('auth.callback', _external=True)
    # prompt=select_account forces Google to show the account picker every time,
    # so signing out and back in always requires an explicit account selection.
    return oauth.google.authorize_redirect(redirect_uri, prompt='select_account')


@auth_bp.route('/auth/callback')
def callback():
    try:
        token = oauth.google.authorize_access_token()
    except Exception:
        flash('Sign-in was cancelled or failed. Please try again.', 'error')
        return redirect(url_for('auth.login'))

    user_info = token.get('userinfo')
    if not user_info:
        flash('Could not retrieve your Google account info. Please try again.', 'error')
        return redirect(url_for('auth.login'))

    allowed_email = os.environ.get('ALLOWED_EMAIL', '')
    if allowed_email and user_info.get('email') != allowed_email:
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(google_id=user_info['sub']).first()
    is_new_user = user is None

    if is_new_user:
        user = User(
            google_id=user_info['sub'],
            email=user_info['email'],
            name=user_info.get('name', user_info['email']),
            picture=user_info.get('picture'),
        )
        db.session.add(user)
        db.session.commit()

        # First user to sign in claims any pre-existing unowned vehicles
        if User.query.count() == 1:
            Vehicle.query.filter_by(user_id=None).update({'user_id': user.id})
            db.session.commit()

    login_user(user, remember=True)
    return redirect(url_for('main.index'))


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
