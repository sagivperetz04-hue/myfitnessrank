import os
import time

import psycopg2
import pytest

TEST_DB_URL = "postgresql://postgres:testpass@localhost:5433/fitrank_test"
os.environ["DATABASE_URL"] = TEST_DB_URL

from app import app as flask_app  # noqa: E402 — env must be set before import


def _wait_for_db(url: str, retries: int = 20) -> None:
    for _ in range(retries):
        try:
            conn = psycopg2.connect(url)
            conn.close()
            return
        except psycopg2.OperationalError:
            time.sleep(0.5)
    raise RuntimeError("Test database never became ready")


def _raw_conn(url: str) -> psycopg2.extensions.connection:
    conn = psycopg2.connect(url)
    conn.autocommit = True
    return conn


@pytest.fixture(scope="session", autouse=True)
def apply_schema_and_seed():
    """Apply schema + seed once per test session."""
    _wait_for_db(TEST_DB_URL)

    base = os.path.join(os.path.dirname(__file__), "..")
    schema_path = os.path.join(base, "schema.sql")
    seed_path = os.path.join(base, "scripts", "seed_global_standards.sql")

    conn = _raw_conn(TEST_DB_URL)
    with conn.cursor() as cur:
        with open(schema_path) as f:
            cur.execute(f.read())
        with open(seed_path) as f:
            cur.execute(f.read())
    conn.close()

    yield

    # Tear down after the full session
    conn = _raw_conn(TEST_DB_URL)
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS workout_logs CASCADE")
        cur.execute("DROP TABLE IF EXISTS users CASCADE")
        cur.execute("DROP TABLE IF EXISTS global_standards CASCADE")
    conn.close()


@pytest.fixture(autouse=True)
def clean_tables(apply_schema_and_seed):
    """Wipe user data between tests; leave global_standards intact."""
    yield
    conn = _raw_conn(TEST_DB_URL)
    with conn.cursor() as cur:
        cur.execute("TRUNCATE workout_logs, users RESTART IDENTITY CASCADE")
    conn.close()


@pytest.fixture(scope="session")
def app():
    flask_app.config["TESTING"] = True
    yield flask_app


@pytest.fixture()
def client(app):
    return app.test_client()
