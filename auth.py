"""
auth.py - Google OAuth + Email/Password auth
"""

import os
from authlib.integrations.flask_client import OAuth
from flask import Blueprint, redirect, url_for, session, request, jsonify
from flask_login import login_user, logout_user, current_user
import database as db
from models import User

auth_bp = Blueprint("auth", __name__)
oauth   = OAuth()

# ─────────────────────────────────────────────────────────────
# Initialize OAuth
# ─────────────────────────────────────────────────────────────
def init_oauth(app):
    app.secret_key = os.environ.get("SECRET_KEY", "dev_secret")

    oauth.init_app(app)

    oauth.register(
        name="google",
        client_id=os.environ.get("GOOGLE_CLIENT_ID"),
        client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={
            "scope": "openid email profile"
        },
    )


# ─────────────────────────────────────────────────────────────
# Google OAuth Login
# ─────────────────────────────────────────────────────────────
@auth_bp.route("/auth/login")
def login():
    if current_user.is_authenticated:
        return redirect("/")

    redirect_uri = url_for("auth.callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


# ─────────────────────────────────────────────────────────────
# Google OAuth Callback
# ─────────────────────────────────────────────────────────────
@auth_bp.route("/auth/callback")
def callback():
    try:
        token = oauth.google.authorize_access_token()

        # ✅ FIXED: use full URL
        resp = oauth.google.get("https://www.googleapis.com/oauth2/v3/userinfo")
        user_info = resp.json()

        print("✅ Google User Info:", user_info)

        if not user_info or "sub" not in user_info:
            return redirect("/login.html?error=google_failed")

        user_row = db.upsert_user(
            google_id=user_info.get("sub"),
            email=user_info.get("email"),
            name=user_info.get("name", ""),
            picture=user_info.get("picture", ""),
        )

        login_user(User(user_row), remember=True)

        return redirect("/")

    except Exception as e:
        print("❌ OAuth Error:", str(e))
        return redirect("/login.html?error=auth_failed")

# ─────────────────────────────────────────────────────────────
# Email / Password Register
# ─────────────────────────────────────────────────────────────
@auth_bp.route("/auth/register", methods=["POST"])
def register():
    body = request.get_json(silent=True) or {}

    email    = body.get("email", "").strip().lower()
    name     = body.get("name", "").strip()
    password = body.get("password", "")

    if not email or not name or not password:
        return jsonify({"error": "All fields are required"}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    user_row = db.register_user(email, name, password)

    if not user_row:
        return jsonify({"error": "Email already registered"}), 409

    login_user(User(user_row), remember=True)

    return jsonify({"message": "Registered successfully"}), 201


# ─────────────────────────────────────────────────────────────
# Email Login
# ─────────────────────────────────────────────────────────────
@auth_bp.route("/auth/email-login", methods=["POST"])
def email_login():
    body = request.get_json(silent=True) or {}

    email    = body.get("email", "").strip().lower()
    password = body.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    user_row = db.login_email_user(email, password)

    if not user_row:
        return jsonify({"error": "Invalid email or password"}), 401

    login_user(User(user_row), remember=True)

    return jsonify({"message": "Login successful"})


# ─────────────────────────────────────────────────────────────
# Logout
# ─────────────────────────────────────────────────────────────
@auth_bp.route("/auth/logout")
def logout():
    logout_user()
    session.clear()
    return redirect("/login.html")


# ─────────────────────────────────────────────────────────────
# Current User Info
# ─────────────────────────────────────────────────────────────
@auth_bp.route("/auth/me")
def me():
    if not current_user.is_authenticated:
        return jsonify({"logged_in": False}), 401

    return jsonify({
        "logged_in": True,
        "id":        current_user.id,
        "name":      current_user.name,
        "email":     current_user.email,
        "picture":   current_user.picture,
        "auth_type": current_user.auth_type,
        "joined":    current_user.joined,
    })