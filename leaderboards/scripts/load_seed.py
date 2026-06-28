#!/usr/bin/env python3
"""Load the compact seed pool into the leaderboard, encrypting names at rest.

Idempotent: replaces all source='seed' rows, leaves user rows untouched. Runs
as the Helm post-install/post-upgrade Job (or manually for local testing).

    DATABASE_URL=... LEADERBOARD_ENC_KEY=... python scripts/load_seed.py
"""

import csv
import os
import sys

import psycopg2
from psycopg2.extras import execute_values

# Importable as services.crypto whether run from /app (image) or the repo.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.crypto import encrypt_name  # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SEED = os.path.join(_HERE, "seed_pool.csv")


def load(seed_path: str, database_url: str) -> int:
    rows = []
    with open(seed_path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            rows.append(
                (
                    r["sex"],
                    "seed",
                    None,
                    encrypt_name(r["name"]),
                    r["bodyweight"],
                    r["squat"],
                    r["bench"],
                    r["deadlift"],
                    r["total"],
                )
            )

    conn = psycopg2.connect(database_url)
    try:
        with conn, conn.cursor() as cur:
            cur.execute("DELETE FROM leaderboard_entries WHERE source = 'seed'")
            execute_values(
                cur,
                """
                INSERT INTO leaderboard_entries
                    (sex, source, user_id, name_enc, bodyweight_kg,
                     squat_kg, bench_kg, deadlift_kg, total_kg)
                VALUES %s
                """,
                rows,
            )
    finally:
        conn.close()
    return len(rows)


def main() -> int:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is not set", file=sys.stderr)
        return 1
    if not os.environ.get("LEADERBOARD_ENC_KEY"):
        print("LEADERBOARD_ENC_KEY is not set", file=sys.stderr)
        return 1
    seed_path = os.environ.get("SEED_FILE", DEFAULT_SEED)
    n = load(seed_path, database_url)
    print(f"loaded {n} seed rows from {seed_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
