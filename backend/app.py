import os
import logging

from flask import Flask, g, jsonify, request

from db import get_connection, return_connection
from services.ranking import (
    assign_tier,
    assign_weight_class,
    calculate_1rm,
    get_percentile,
)
from services.leaderboard import get_top_lifters, submit_bests
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

from prometheus_client import Counter, Histogram  # noqa: E402

RANKS_TOTAL = Counter(
    "fitrank_ranks_total",
    "Lifts ranked, by exercise, sex, and competition tier",
    ["exercise", "sex", "tier"],
)
ONE_RM_KG = Histogram(
    "fitrank_one_rm_kg",
    "Estimated 1RM of ranked lifts (kg)",
    ["exercise"],
    # Spans a beginner bench (~40) through a world-record deadlift (~505);
    # "total" submissions land in the top buckets.
    buckets=(40, 60, 80, 100, 130, 160, 200, 250, 320, 400, 500, 700, 1000),
)
LEADERBOARD_SYNC_TOTAL = Counter(
    "fitrank_leaderboard_sync_total",
    "Best-lift forwards to the leaderboards service, by outcome",
    ["outcome"],
)

_VALID_EXERCISES = ("squat", "bench", "deadlift", "total")

# All-time world records (kg); must stay in sync with WORLD_RECORDS in
# frontend/src/App.jsx — the browser check is UX, this one is the gate
_WORLD_RECORDS_KG = {
    "squat": 525,
    "bench": 355,
    "deadlift": 505,
    "total": 1152.5,
}
_WR_MARGIN_KG = 2

# Heaviest human ever recorded weighed 635 kg — past that it's a vehicle,
# not a lifter. Same philosophy as the lift cap: real-world record + margin.
_BODYWEIGHT_CAP_KG = 640


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
        return_connection(conn)  # returns to pool; discards if broken


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


def _sync_leaderboard(conn, user_id, sex, bodyweight_kg, bearer):
    """Push the user's best lifts to the leaderboards service.

    Best-effort: the lift is already logged, so a leaderboards outage must not
    fail the rank response. The board needs a full total, so nothing is sent
    until squat, bench, and deadlift have all been logged at least once.
    """
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT exercise, MAX(one_rm_kg) AS best FROM workout_logs "
                "WHERE user_id = %s AND exercise IN ('squat', 'bench', 'deadlift') "
                "GROUP BY exercise",
                (user_id,),
            )
            bests = {r["exercise"]: float(r["best"]) for r in cur.fetchall()}
        if set(bests) != {"squat", "bench", "deadlift"}:
            LEADERBOARD_SYNC_TOTAL.labels(outcome="incomplete").inc()
            return
        submit_bests(bearer, sex, bodyweight_kg, bests)
        LEADERBOARD_SYNC_TOTAL.labels(outcome="synced").inc()
        log.info("leaderboard sync ok user_id=%s sex=%s", user_id, sex)
    except Exception as exc:
        LEADERBOARD_SYNC_TOTAL.labels(outcome="failed").inc()
        log.warning("leaderboard sync failed (lift still logged): %s", exc)


@app.route("/api/rank", methods=["POST"])
def rank():
    body = request.get_json(silent=True) or {}
    required = ("username", "exercise", "weight_kg", "reps", "bodyweight_kg", "sex")
    missing = [f for f in required if f not in body]
    if missing:
        return jsonify({"error": f"missing fields: {missing}"}), 400

    exercise = body["exercise"]
    sex = str(body["sex"]).upper()

    # A signed-in lift is recorded under the token's identity, never the body's:
    # otherwise any authenticated user could write history under someone else's
    # username. A present-but-invalid token is rejected rather than falling back
    # to the body (that fallback would be the bypass). No token = guest mode,
    # where the body username is trusted (browser-local, unauthenticated).
    auth_header = request.headers.get("Authorization", "")
    claims = None
    if auth_header.startswith("Bearer "):
        try:
            claims = decode_access(auth_header[len("Bearer ") :])
        except TokenError:
            return jsonify({"error": "invalid or expired token"}), 401
    username = claims["username"] if claims else body["username"]

    if not username or not str(username).strip():
        return jsonify({"error": "username must not be empty"}), 400
    if sex not in ("M", "F"):
        return jsonify({"error": "sex must be M or F"}), 400
    if exercise not in _VALID_EXERCISES:
        return jsonify({"error": f"exercise must be one of {_VALID_EXERCISES}"}), 400

    try:
        weight_kg = float(body["weight_kg"])
        reps = int(body["reps"])
        bodyweight_kg = float(body["bodyweight_kg"])
    except (ValueError, TypeError):
        return jsonify(
            {
                "error": "weight_kg and bodyweight_kg must be numbers, reps must be an integer"
            }
        ), 400

    if weight_kg <= 0 or bodyweight_kg <= 0 or reps <= 0:
        return jsonify(
            {"error": "weight_kg, bodyweight_kg, and reps must be positive"}
        ), 400
    if reps > 20:
        return jsonify(
            {"error": "reps must be 20 or fewer — Epley formula is unreliable above 20"}
        ), 400
    weight_cap_kg = _WORLD_RECORDS_KG[exercise] + _WR_MARGIN_KG
    if weight_kg > weight_cap_kg:
        return jsonify(
            {
                "error": (
                    f"weight_kg must be at most {weight_cap_kg} kg for {exercise} "
                    "— that would beat the world record"
                )
            }
        ), 400
    if bodyweight_kg > _BODYWEIGHT_CAP_KG:
        return jsonify(
            {
                "error": (
                    f"bodyweight_kg must be at most {_BODYWEIGHT_CAP_KG} kg "
                    "— the heaviest human ever recorded weighed 635 kg"
                )
            }
        ), 400

    one_rm_kg = calculate_1rm(weight_kg, reps)
    weight_class = assign_weight_class(bodyweight_kg, sex)

    try:
        conn = _db()

        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (username) VALUES (%s) ON CONFLICT (username) DO NOTHING",
                (username,),
            )
            cur.execute("SELECT id FROM users WHERE username = %s", (username,))
            user_id = cur.fetchone()["id"]

        comp_percentile = get_percentile(
            conn, exercise, sex, bodyweight_kg, one_rm_kg, "competition"
        )
        comp_tier = assign_tier(comp_percentile)
        avg_percentile = get_percentile(
            conn, exercise, sex, bodyweight_kg, one_rm_kg, "world_avg"
        )
        avg_tier = assign_tier(avg_percentile)

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO workout_logs
                  (user_id, exercise, weight_kg, reps, one_rm_kg,
                   bodyweight_kg, sex, weight_class_kg,
                   competition_percentile, competition_tier,
                   world_avg_percentile, world_avg_tier)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    user_id,
                    exercise,
                    weight_kg,
                    reps,
                    one_rm_kg,
                    bodyweight_kg,
                    sex,
                    weight_class,
                    comp_percentile,
                    comp_tier,
                    avg_percentile,
                    avg_tier,
                ),
            )
            conn.commit()
    except Exception as exc:
        log.error("db error in /api/rank: %s", exc)
        return jsonify({"error": "database error"}), 500

    RANKS_TOTAL.labels(exercise=exercise, sex=sex, tier=comp_tier).inc()
    ONE_RM_KG.labels(exercise=exercise).observe(one_rm_kg)

    log.info(
        "ranked user=%s exercise=%s 1rm=%.1f comp=%d(%s) world_avg=%d(%s)",
        username,
        exercise,
        one_rm_kg,
        comp_percentile,
        comp_tier,
        avg_percentile,
        avg_tier,
    )

    # Signed-in lifters feed the leaderboard; the leaderboards service re-verifies
    # the same token and dedups server-side.
    if claims:
        _sync_leaderboard(conn, user_id, sex, bodyweight_kg, auth_header)

    return jsonify(
        {
            "one_rm_kg": one_rm_kg,
            "weight_class_kg": weight_class,
            "competition": {"percentile": comp_percentile, "tier": comp_tier},
            "world_avg": {"percentile": avg_percentile, "tier": avg_tier},
        }
    ), 200


@app.route("/api/users/<username>/history", methods=["GET"])
def user_history(username):
    exercise = request.args.get("exercise")
    if exercise and exercise not in _VALID_EXERCISES:
        return jsonify({"error": f"exercise must be one of {_VALID_EXERCISES}"}), 400

    try:
        limit = min(int(request.args.get("limit", 20)), 100)
        offset = max(int(request.args.get("offset", 0)), 0)
    except (ValueError, TypeError):
        return jsonify({"error": "limit and offset must be integers"}), 400

    try:
        conn = _db()
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE username = %s", (username,))
            user = cur.fetchone()

        if user is None:
            return jsonify({"error": "user not found"}), 404

        with conn.cursor() as cur:
            if exercise:
                cur.execute(
                    """
                    SELECT id, exercise, weight_kg, reps, one_rm_kg,
                           bodyweight_kg, sex, weight_class_kg,
                           competition_percentile, competition_tier,
                           world_avg_percentile, world_avg_tier,
                           logged_at
                    FROM workout_logs
                    WHERE user_id = %s AND exercise = %s
                    ORDER BY logged_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (user["id"], exercise, limit, offset),
                )
            else:
                cur.execute(
                    """
                    SELECT id, exercise, weight_kg, reps, one_rm_kg,
                           bodyweight_kg, sex, weight_class_kg,
                           competition_percentile, competition_tier,
                           world_avg_percentile, world_avg_tier,
                           logged_at
                    FROM workout_logs
                    WHERE user_id = %s
                    ORDER BY logged_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (user["id"], limit, offset),
                )
            rows = cur.fetchall()
    except Exception as exc:
        log.error("db error in /api/users/history: %s", exc)
        return jsonify({"error": "database error"}), 500

    return jsonify(
        {
            "username": username,
            "logs": [_format_log(r) for r in rows],
        }
    ), 200


@app.route("/api/users/<username>/best", methods=["GET"])
def user_best(username):
    try:
        conn = _db()
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE username = %s", (username,))
            user = cur.fetchone()

        if user is None:
            return jsonify({"error": "user not found"}), 404

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT ON (exercise)
                    id, exercise, weight_kg, reps, one_rm_kg,
                    bodyweight_kg, sex, weight_class_kg,
                    competition_percentile, competition_tier,
                    world_avg_percentile, world_avg_tier,
                    logged_at
                FROM workout_logs
                WHERE user_id = %s
                ORDER BY exercise, one_rm_kg DESC
                """,
                (user["id"],),
            )
            rows = cur.fetchall()
    except Exception as exc:
        log.error("db error in /api/users/best: %s", exc)
        return jsonify({"error": "database error"}), 500

    return jsonify(
        {
            "username": username,
            "bests": {r["exercise"]: _format_log(r) for r in rows},
        }
    ), 200


@app.route("/api/leaderboard", methods=["GET"])
def leaderboard():
    sex = (request.args.get("sex") or "").upper()
    weight_class = request.args.get("weight_class", "")
    lift = request.args.get("lift", "")

    if sex not in ("M", "F"):
        return jsonify({"error": "sex must be M or F"}), 400
    if lift not in _VALID_EXERCISES:
        return jsonify({"error": f"lift must be one of {_VALID_EXERCISES}"}), 400
    if not weight_class:
        return jsonify({"error": "weight_class is required"}), 400

    try:
        data = get_top_lifters(sex, weight_class, lift)
    except Exception as exc:
        log.error("leaderboard fetch failed: %s", exc)
        return jsonify({"error": "upstream unavailable"}), 502

    return jsonify({"lifters": data}), 200


def _format_log(row) -> dict:
    return {
        "id": row["id"],
        "exercise": row["exercise"],
        "weight_kg": float(row["weight_kg"]),
        "reps": row["reps"],
        "one_rm_kg": float(row["one_rm_kg"]),
        "bodyweight_kg": float(row["bodyweight_kg"]),
        "sex": row["sex"],
        "weight_class_kg": row["weight_class_kg"],
        "competition": {
            "percentile": row["competition_percentile"],
            "tier": row["competition_tier"],
        },
        "world_avg": {
            "percentile": row["world_avg_percentile"],
            "tier": row["world_avg_tier"],
        },
        "logged_at": row["logged_at"].isoformat(),
    }


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
