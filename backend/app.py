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
from services.leaderboard import get_top_lifters

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

app = Flask(__name__)

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


@app.route("/api/rank", methods=["POST"])
def rank():
    body = request.get_json(silent=True) or {}
    required = ("username", "exercise", "weight_kg", "reps", "bodyweight_kg", "sex")
    missing = [f for f in required if f not in body]
    if missing:
        return jsonify({"error": f"missing fields: {missing}"}), 400

    exercise = body["exercise"]
    sex = str(body["sex"]).upper()
    username = body["username"]

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
