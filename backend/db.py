import os
import threading

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool

# Initialized lazily — must happen AFTER gunicorn forks workers, never before.
# Each worker process gets its own independent pool (safe with pre-fork model).
_pool: ThreadedConnectionPool | None = None
_lock = threading.Lock()


def _get_pool() -> ThreadedConnectionPool:
    global _pool
    if _pool is None:
        with _lock:
            if _pool is None:  # double-checked — only one thread creates the pool
                _pool = ThreadedConnectionPool(
                    int(os.environ.get("DB_POOL_MIN", 1)),
                    int(os.environ.get("DB_POOL_MAX", 5)),
                    os.environ["DATABASE_URL"],
                    cursor_factory=RealDictCursor,
                )
    return _pool


def get_connection() -> psycopg2.extensions.connection:
    return _get_pool().getconn()


def return_connection(conn: psycopg2.extensions.connection) -> None:
    # close=True discards a broken connection instead of returning it to the pool.
    # conn.closed is 0 when healthy, non-zero when the socket is gone.
    _get_pool().putconn(conn, close=conn.closed != 0)
