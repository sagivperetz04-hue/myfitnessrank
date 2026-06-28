import logging
import os

from flask import Flask, g, jsonify, request

from db import get_connection, return_connection
from services.board import VALID_SEXES, top_entries, submit_lift
from services.tokens import TokenError, decode_access

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

app = Flask(__name__)


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


@app.route("/health/live")
def health_live():
    # Liveness must not touch the DB: a transient DB outage should pull the pod
    # from rotation (readiness), not restart it (a restart can't fix the DB and
    # only causes cascading churn). This only proves the process is up.
    return jsonify({"status": "ok"}), 200


@app.route("/health")
def health():
    # Readiness: only route traffic here while the DB is reachable.
    try:
        conn = _db()
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
    except Exception as exc:
        log.error("health check db ping failed: %s", exc)
        return jsonify({"status": "error", "detail": "db unavailable"}), 503
    return jsonify({"status": "ok"}), 200


def _claims_from_request():
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise TokenError("missing bearer token")
    return decode_access(header[len("Bearer ") :])


def _positive_number(body: dict, field: str):
    """Return a float > 0 for `field`, or None if missing/invalid/non-positive."""
    try:
        value = float(body.get(field))
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


@app.route("/api/leaderboards", methods=["GET"])
def leaderboards():
    sex = request.args.get("sex", "").upper()
    if sex not in VALID_SEXES:
        return jsonify({"error": "sex must be M or F"}), 400
    sort = request.args.get("sort", "total")
    limit = request.args.get("limit", 200)
    try:
        conn = _db()
        entries = top_entries(conn, sex, sort, limit)
    except Exception as exc:
        log.error("db error in /leaderboards: %s", exc)
        return jsonify({"error": "database error"}), 500
    return jsonify({"sex": sex, "sort": sort, "entries": entries}), 200


@app.route("/api/leaderboards/submit", methods=["POST"])
def submit():
    try:
        claims = _claims_from_request()
    except TokenError:
        return jsonify({"error": "invalid or expired token"}), 401

    body = request.get_json(silent=True) or {}
    sex = str(body.get("sex", "")).upper()
    if sex not in VALID_SEXES:
        return jsonify({"error": "sex must be M or F"}), 400

    lifts = {}
    for field in ("squat_kg", "bench_kg", "deadlift_kg", "bodyweight_kg"):
        value = _positive_number(body, field)
        if value is None:
            return jsonify({"error": f"{field} must be a positive number"}), 400
        lifts[field] = value

    try:
        conn = _db()
        entry = submit_lift(
            conn,
            sex=sex,
            user_id=int(claims["sub"]),
            username=claims["username"],
            squat_kg=lifts["squat_kg"],
            bench_kg=lifts["bench_kg"],
            deadlift_kg=lifts["deadlift_kg"],
            bodyweight_kg=lifts["bodyweight_kg"],
        )
    except Exception as exc:
        log.error("db error in /submit: %s", exc)
        return jsonify({"error": "database error"}), 500

    log.info(
        "leaderboard submit user_id=%s sex=%s total=%s rank=%s",
        claims["sub"],
        sex,
        entry["total_kg"],
        entry["rank"],
    )
    return jsonify({"entry": entry}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
