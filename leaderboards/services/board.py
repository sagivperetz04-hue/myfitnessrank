from services.crypto import decrypt_name, encrypt_name

# Whitelist: maps the public `sort` query value to a real column. Lookups here
# are the ONLY way a column name reaches the SQL string, so sorting can never
# be an injection vector.
SORT_COLUMNS = {
    "total": "total_kg",
    "ratio": "bw_ratio",
    "bench": "bench_kg",
    "deadlift": "deadlift_kg",
    "squat": "squat_kg",
}
DEFAULT_SORT = "total"

VALID_SEXES = ("M", "F")
MAX_LIMIT = 200
# Ranking at or above this triggers the congratulations/verification mail
TOP_N = 200


def sort_column(sort: str) -> str:
    """Resolve a public sort key to its column, falling back to total."""
    return SORT_COLUMNS.get(sort, SORT_COLUMNS[DEFAULT_SORT])


def clamp_limit(limit) -> int:
    try:
        n = int(limit)
    except (TypeError, ValueError):
        return MAX_LIMIT
    return max(1, min(n, MAX_LIMIT))


def _row_to_public(rank: int, row: dict) -> dict:
    return {
        "rank": rank,
        "name": decrypt_name(row["name_enc"]),
        "bodyweight_kg": float(row["bodyweight_kg"]),
        "squat_kg": float(row["squat_kg"]),
        "bench_kg": float(row["bench_kg"]),
        "deadlift_kg": float(row["deadlift_kg"]),
        "total_kg": float(row["total_kg"]),
        "bw_ratio": float(row["bw_ratio"]),
        "source": row["source"],
    }


def top_entries(conn, sex: str, sort: str, limit: int) -> list[dict]:
    col = sort_column(sort)
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT name_enc, bodyweight_kg, squat_kg, bench_kg, deadlift_kg,
                   total_kg, bw_ratio, source
            FROM leaderboard_entries
            WHERE sex = %s
            ORDER BY {col} DESC, total_kg DESC, id ASC
            LIMIT %s
            """,
            (sex, clamp_limit(limit)),
        )
        rows = cur.fetchall()
    return [_row_to_public(i + 1, r) for i, r in enumerate(rows)]


def submit_lift(
    conn,
    sex: str,
    user_id: int,
    username: str,
    squat_kg: float,
    bench_kg: float,
    deadlift_kg: float,
    bodyweight_kg: float,
) -> tuple[dict, dict]:
    """Upsert the user's row, keeping the best of each lift (overwrite-when-better).

    One row per (sex, user_id). total_kg is recomputed from the kept per-lift
    bests; bw_ratio is a generated column that follows total_kg automatically.

    Returns (public_entry, meta) — meta carries the row id and notified_at so
    the caller can decide whether the top-200 mail is still owed.
    """
    name_enc = encrypt_name(username)
    total_kg = squat_kg + bench_kg + deadlift_kg
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO leaderboard_entries
                (sex, source, user_id, name_enc, bodyweight_kg,
                 squat_kg, bench_kg, deadlift_kg, total_kg)
            VALUES (%s, 'user', %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (sex, user_id) WHERE source = 'user'
            DO UPDATE SET
                squat_kg      = GREATEST(leaderboard_entries.squat_kg, EXCLUDED.squat_kg),
                bench_kg      = GREATEST(leaderboard_entries.bench_kg, EXCLUDED.bench_kg),
                deadlift_kg   = GREATEST(leaderboard_entries.deadlift_kg, EXCLUDED.deadlift_kg),
                bodyweight_kg = EXCLUDED.bodyweight_kg,
                name_enc      = EXCLUDED.name_enc,
                total_kg      = GREATEST(leaderboard_entries.squat_kg, EXCLUDED.squat_kg)
                              + GREATEST(leaderboard_entries.bench_kg, EXCLUDED.bench_kg)
                              + GREATEST(leaderboard_entries.deadlift_kg, EXCLUDED.deadlift_kg),
                updated_at    = NOW()
            RETURNING id, notified_at, name_enc, bodyweight_kg, squat_kg, bench_kg,
                      deadlift_kg, total_kg, bw_ratio, source
            """,
            (
                sex,
                user_id,
                name_enc,
                bodyweight_kg,
                squat_kg,
                bench_kg,
                deadlift_kg,
                total_kg,
            ),
        )
        row = cur.fetchone()
        cur.execute(
            "SELECT COUNT(*) + 1 AS rank FROM leaderboard_entries "
            "WHERE sex = %s AND total_kg > %s",
            (sex, row["total_kg"]),
        )
        rank = cur.fetchone()["rank"]
    conn.commit()
    meta = {"id": row["id"], "notified_at": row["notified_at"]}
    return _row_to_public(rank, row), meta


def mark_notified(conn, entry_id: int) -> None:
    """Stamp an entry after its top-200 mail went out, so it is sent only once."""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE leaderboard_entries SET notified_at = NOW() WHERE id = %s",
            (entry_id,),
        )
    conn.commit()
