import logging
import os

from flask import Flask, g, jsonify, request

from db import get_connection, return_connection
from services.board import (
    TOP_N,
    VALID_SEXES,
    WORLD_RECORDS_KG,
    board_size,
    lift_cap,
    mark_notified,
    top_entries,
    submit_lift,
)
from services.mailer import send_top200_mail
from services.tokens import TokenError, decode_access

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

app = Flask(__name__)

# Prometheus metrics at /metrics. Under gunicorn (multiple workers) counters are
# aggregated across workers via a shared dir (PROMETHEUS_MULTIPROC_DIR, set in the
# image); tests and `python app.py` run single-process without it. The Internal
# variant serves /metrics from the app port itself (which the ServiceMonitor
# scrapes) — the non-Internal one registers no route and expects a separate
# metrics server, leaving /metrics a 404.
if os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
    from prometheus_flask_exporter.multiprocess import (
        GunicornInternalPrometheusMetrics,
    )

    metrics = GunicornInternalPrometheusMetrics(app)
else:
    from prometheus_flask_exporter import PrometheusMetrics

    metrics = PrometheusMetrics(app)

from prometheus_client import Counter, Gauge  # noqa: E402

SUBMISSIONS_TOTAL = Counter(
    "fitrank_board_submissions_total",
    "Accepted leaderboard submissions, by sex",
    ["sex"],
)
# Set from a DB count, so every worker reports the same truth — take the value
# from whichever live worker wrote it last instead of summing across workers.
BOARD_SIZE = Gauge(
    "fitrank_board_size",
    "Rows on the leaderboard, by sex",
    ["sex"],
    multiprocess_mode="livemostrecent",
)
TOP200_MAILS_TOTAL = Counter(
    "fitrank_top200_mails_total",
    "Top-200 congratulation mails, by outcome",
    ["outcome"],
)


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
        BOARD_SIZE.labels(sex=sex).set(board_size(conn, sex))
    except Exception as exc:
        log.error("db error in /leaderboards: %s", exc)
        return jsonify({"error": "database error"}), 500
    return jsonify({"sex": sex, "sort": sort, "entries": entries}), 200


def _maybe_send_top200_mail(conn, claims, entry, meta):
    """Congratulate a lifter the first time their entry ranks in the top 200.

    The entry is stamped only after the mail goes out, so a delivery failure
    retries on the next submit; once stamped it is never sent again. Verification
    itself is manual for now — the mail asks for video + bodyweight proof.
    """
    if entry["rank"] > TOP_N or meta["notified_at"] is not None:
        return
    email = claims.get("email")
    if not email:
        log.warning("top-200 entry id=%s has no email claim; mail skipped", meta["id"])
        return
    try:
        send_top200_mail(email, claims["username"], entry["rank"], entry["total_kg"])
        mark_notified(conn, meta["id"])
        TOP200_MAILS_TOTAL.labels(outcome="sent").inc()
        log.info("top-200 mail sent user_id=%s rank=%s", claims["sub"], entry["rank"])
    except Exception as exc:
        TOP200_MAILS_TOTAL.labels(outcome="failed").inc()
        log.warning("top-200 mail failed (will retry on next submit): %s", exc)


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
        # A total is only credible if each lift is; reject anything past the
        # world record so a direct POST can't manufacture a #1 entry.
        if field in WORLD_RECORDS_KG and value > lift_cap(field):
            return jsonify(
                {
                    "error": f"{field} exceeds the accepted maximum of {lift_cap(field)} kg"
                }
            ), 400
        lifts[field] = value

    try:
        conn = _db()
        entry, meta = submit_lift(
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

    SUBMISSIONS_TOTAL.labels(sex=sex).inc()
    try:
        BOARD_SIZE.labels(sex=sex).set(board_size(conn, sex))
    except Exception as exc:
        log.warning("board size gauge update failed: %s", exc)

    _maybe_send_top200_mail(conn, claims, entry, meta)

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
