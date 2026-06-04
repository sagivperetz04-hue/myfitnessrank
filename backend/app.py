import os
import logging

from flask import Flask, g, jsonify, request

from db import get_connection
from services.ranking import (
    assign_tier,
    assign_weight_class,
    calculate_1rm,
    get_percentile,
)
from services.leaderboard import get_top_lifters

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

app = Flask(__name__)

_VALID_EXERCISES = ('squat', 'bench', 'deadlift', 'total')
_VALID_TRACKS    = ('world_avg', 'competition')


def _db():
    if 'db' not in g:
        g.db = get_connection()
    return g.db


@app.teardown_appcontext
def _close_db(exc):
    conn = g.pop('db', None)
    if conn is not None:
        conn.close()


@app.route('/health')
def health():
    return jsonify({"status": "ok"}), 200


@app.route('/api/rank', methods=['POST'])
def rank():
    body = request.get_json(silent=True) or {}
    required = ('username', 'exercise', 'weight_kg', 'reps', 'bodyweight_kg', 'sex', 'track')
    missing = [f for f in required if f not in body]
    if missing:
        return jsonify({"error": f"missing fields: {missing}"}), 400

    exercise      = body['exercise']
    weight_kg     = float(body['weight_kg'])
    reps          = int(body['reps'])
    bodyweight_kg = float(body['bodyweight_kg'])
    sex           = str(body['sex']).upper()
    track         = body['track']
    username      = body['username']

    if sex not in ('M', 'F'):
        return jsonify({"error": "sex must be M or F"}), 400
    if track not in _VALID_TRACKS:
        return jsonify({"error": f"track must be one of {_VALID_TRACKS}"}), 400
    if exercise not in _VALID_EXERCISES:
        return jsonify({"error": f"exercise must be one of {_VALID_EXERCISES}"}), 400

    one_rm_kg    = calculate_1rm(weight_kg, reps)
    weight_class = assign_weight_class(bodyweight_kg, sex)
    conn         = _db()

    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO users (username) VALUES (%s) ON CONFLICT (username) DO NOTHING",
            (username,),
        )
        cur.execute("SELECT id FROM users WHERE username = %s", (username,))
        user_id = cur.fetchone()['id']

    percentile = get_percentile(conn, exercise, sex, bodyweight_kg, one_rm_kg, track)
    tier       = assign_tier(percentile)

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO workout_logs
              (user_id, exercise, weight_kg, reps, one_rm_kg, tier,
               world_avg_percentile, competition_percentile)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                user_id, exercise, weight_kg, reps, one_rm_kg, tier,
                percentile if track == 'world_avg' else None,
                percentile if track == 'competition' else None,
            ),
        )
        conn.commit()

    log.info("ranked user=%s exercise=%s 1rm=%.1f percentile=%d tier=%s",
             username, exercise, one_rm_kg, percentile, tier)

    return jsonify({
        "one_rm_kg":       one_rm_kg,
        "weight_class_kg": weight_class,
        "percentile":      percentile,
        "tier":            tier,
    }), 200


@app.route('/api/leaderboard', methods=['GET'])
def leaderboard():
    sex          = (request.args.get('sex') or '').upper()
    weight_class = request.args.get('weight_class', '')
    lift         = request.args.get('lift', '')

    if sex not in ('M', 'F'):
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


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
