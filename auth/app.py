import os
import logging

import psycopg2
from flask import Flask, g, jsonify, request

from db import get_connection, return_connection
from services.security import (
    hash_password,
    is_valid_email,
    password_problems,
    username_problems,
    verify_password,
)
from services.tokens import (
    REFRESH_TTL_SECONDS,
    TokenError,
    decode,
    issue_access,
    issue_refresh,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

app = Flask(__name__)

_REFRESH_COOKIE = "mfr_refresh"
# Scope the refresh cookie to the auth endpoints only — it is never sent to the
# other services. Secure is on by default (modern browsers accept Secure cookies
# on http://localhost); set COOKIE_SECURE=false only for non-localhost http.
_COOKIE_PATH = "/api/auth"
_COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "true").lower() == "true"


def _db():
    if "db" not in g:
        g.db = get_connection()
    return g.db


@app.teardown_appcontext
def _close_db(exc):
    conn = g.pop("db", None)
    if conn is not None:
        if exc is not None and conn.closed == 0:
            conn.rollback()
        return_connection(conn)


@app.route("/health")
def health():
    try:
        conn = _db()
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
    except Exception as exc:
        log.error("health check db ping failed: %s", exc)
        return jsonify({"status": "error", "detail": "db unavailable"}), 503
    return jsonify({"status": "ok"}), 200


def _set_refresh_cookie(resp, account: dict):
    resp.set_cookie(
        _REFRESH_COOKIE,
        issue_refresh(account),
        max_age=REFRESH_TTL_SECONDS,
        httponly=True,
        secure=_COOKIE_SECURE,
        samesite="Strict",
        path=_COOKIE_PATH,
    )


def _public(account: dict) -> dict:
    return {
        "id": account["id"],
        "email": account["email"],
        "username": account["username"],
    }


def _session_response(account: dict, status: int):
    body = {"user": _public(account), "access_token": issue_access(account)}
    resp = jsonify(body)
    _set_refresh_cookie(resp, account)
    return resp, status


@app.route("/api/auth/username-available", methods=["GET"])
def username_available():
    username = request.args.get("username", "").strip()
    if username_problems(username):
        return jsonify({"available": False}), 200
    try:
        conn = _db()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM accounts WHERE LOWER(username) = LOWER(%s)", (username,)
            )
            taken = cur.fetchone() is not None
    except Exception as exc:
        log.error("db error in /username-available: %s", exc)
        return jsonify({"error": "database error"}), 500
    return jsonify({"available": not taken}), 200


@app.route("/api/auth/signup", methods=["POST"])
def signup():
    body = request.get_json(silent=True) or {}
    email = str(body.get("email", "")).strip().lower()
    username = str(body.get("username", "")).strip()
    password = str(body.get("password", ""))

    if not is_valid_email(email):
        return jsonify({"error": "enter a valid email address"}), 400
    uname_problems = username_problems(username)
    if uname_problems:
        return jsonify({"error": "username needs " + ", ".join(uname_problems)}), 400
    problems = password_problems(password)
    if problems:
        return jsonify({"error": "password needs " + ", ".join(problems)}), 400

    try:
        conn = _db()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO accounts (email, username, password_hash)
                VALUES (%s, %s, %s)
                RETURNING id, email, username
                """,
                (email, username, hash_password(password)),
            )
            account = cur.fetchone()
        conn.commit()
    except psycopg2.errors.UniqueViolation as exc:
        conn.rollback()
        # Tell the user which field collided instead of a generic conflict. The
        # username gate is the LOWER(username) index; email is its own constraint.
        if "username" in (exc.diag.constraint_name or ""):
            return jsonify({"error": "that username is taken"}), 409
        return jsonify({"error": "an account with that email already exists"}), 409
    except Exception as exc:
        log.error("db error in /signup: %s", exc)
        return jsonify({"error": "database error"}), 500

    log.info("account created id=%s username=%s", account["id"], account["username"])
    return _session_response(account, 201)


@app.route("/api/auth/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    email = str(body.get("email", "")).strip().lower()
    password = str(body.get("password", ""))

    try:
        conn = _db()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, email, username, password_hash FROM accounts WHERE email = %s",
                (email,),
            )
            account = cur.fetchone()
    except Exception as exc:
        log.error("db error in /login: %s", exc)
        return jsonify({"error": "database error"}), 500

    # Same response for unknown email and wrong password — don't leak which.
    if account is None or not verify_password(account["password_hash"], password):
        return jsonify({"error": "invalid email or password"}), 401

    log.info("login id=%s username=%s", account["id"], account["username"])
    return _session_response(account, 200)


@app.route("/api/auth/refresh", methods=["POST"])
def refresh():
    token = request.cookies.get(_REFRESH_COOKIE)
    if not token:
        return jsonify({"error": "no refresh token"}), 401
    try:
        claims = decode(token, "refresh")
    except TokenError as exc:
        log.info("refresh rejected: %s", exc)
        return jsonify({"error": "invalid or expired session"}), 401

    account = {
        "id": int(claims["sub"]),
        "email": claims["email"],
        "username": claims["username"],
    }
    return jsonify(
        {"user": _public(account), "access_token": issue_access(account)}
    ), 200


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    resp = jsonify({"status": "ok"})
    resp.delete_cookie(_REFRESH_COOKIE, path=_COOKIE_PATH)
    return resp, 200


@app.route("/api/auth/me", methods=["GET"])
def me():
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return jsonify({"error": "missing bearer token"}), 401
    try:
        claims = decode(header[len("Bearer ") :], "access")
    except TokenError:
        return jsonify({"error": "invalid or expired token"}), 401

    return jsonify(
        {
            "user": {
                "id": int(claims["sub"]),
                "email": claims["email"],
                "username": claims["username"],
            }
        }
    ), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
