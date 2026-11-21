"""Phase 3: login, register, logout, permission helpers."""
import os, re
from functools import wraps
from urllib.parse import urlparse
import psycopg2
from dotenv import load_dotenv
from flask import Blueprint, jsonify, redirect, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash
from db import get_connection

load_dotenv()
auth_bp = Blueprint("auth", __name__)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PROTECTED_PAGES = ("/map", "/tables", "/carte")   # need a logged-in user
PROTECT_WRITES = True    # POST/PUT/DELETE on /api/ need login (set False to demo the old PDF page)


def current_user():
    """Returns {id, email, role} or None."""
    if not session.get("uid"):
        return None
    return {"id": session["uid"], "email": session["email"], "role": session["role"]}


def can_modify(created_by):
    """Admin can edit everything; a user only what they created."""
    u = current_user()
    return bool(u) and (u["role"] == "admin" or (created_by is not None and created_by == u["id"]))


def login_required(f):
    @wraps(f)
    def wrapper(*a, **k):
        if not current_user():
            if request.path.startswith("/api/"):
                return jsonify({"error": "Connexion requise."}), 401
            return redirect("/login")
        return f(*a, **k)
    return wrapper


def _safe_next(url):
    # Only allow redirects to paths on this site
    return url if url and url.startswith("/") and not url.startswith("//") else "/map"


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html", error=None, email="", next=request.args.get("next", ""))
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, password_hash, role FROM users WHERE email = %s", (email,))
            row = cur.fetchone()
    finally:
        conn.close()
    if not row or not check_password_hash(row[1], password):
        return render_template("login.html", error="E-mail ou mot de passe incorrect.", email=email,
                               next=request.form.get("next", "")), 401
    session.clear()
    session.update(uid=row[0], email=email, role=row[2])
    return redirect(_safe_next(request.form.get("next")))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html", error=None, email="")
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    confirm = request.form.get("confirm") or ""
    error = None
    if not EMAIL_RE.match(email) or len(email) > 254:
        error = "Adresse e-mail invalide."
    elif len(password) < 8:
        error = "Le mot de passe doit contenir au moins 8 caractères."
    elif password != confirm:
        error = "Les mots de passe ne correspondent pas."
    if error:
        return render_template("register.html", error=error, email=email), 400
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO users (email, password_hash) VALUES (%s, %s) RETURNING id, role",
                        (email, generate_password_hash(password)))
            uid, role = cur.fetchone()
        conn.commit()
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return render_template("register.html", error="Cette adresse e-mail est déjà utilisée.", email=email), 409
    finally:
        conn.close()
    session.clear()
    session.update(uid=uid, email=email, role=role)
    return redirect("/map")


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/home")


def init_auth(app):
    """Call once in app.py after app = Flask(...)"""
    app.secret_key = os.getenv("SECRET_KEY") or "dev-only-change-me"
    app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")
    app.register_blueprint(auth_bp)

    @app.context_processor
    def inject_user():           # makes `current_user` available in every template
        return {"current_user": current_user()}

    @app.before_request
    def guard():
        if request.path.startswith(PROTECTED_PAGES) and not current_user():
            return redirect("/login?next=" + request.path)
        if (PROTECT_WRITES and request.path.startswith("/api/")
                and request.method in ("POST", "PUT", "PATCH", "DELETE") and not current_user()):
            return jsonify({"error": "Connexion requise."}), 401