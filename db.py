# db.py — Database connection helper.
#
# Design decisions:
#   - One connection is opened per request and closed explicitly after use.
#   - psycopg2's `with conn:` context manager only commits/rolls back the
#     transaction; it does NOT close the connection. We close it ourselves.
#   - Credentials are read from the .env file via python-dotenv.
#   - On failure, we raise a RuntimeError with a friendly message so the
#     Flask route can return a 503 response instead of a raw stack trace.

import logging
import os

import psycopg2
from dotenv import load_dotenv

# Load .env from the directory that contains this file.
# This works whether Flask is started from soil-platform/ or its parent.
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

logger = logging.getLogger(__name__)


def get_connection():
    """Open and return a new psycopg2 connection using .env credentials.

    Why open a new connection per request rather than a pool?
    For a local academic project with low concurrency, a simple
    connect-per-request approach is easier to understand and debug.
    A production app would use a connection pool (e.g. psycopg2.pool).

    Raises:
        RuntimeError: if the database is unreachable or credentials are wrong.
                      The message is safe to show in a 503 response.

    Returns:
        psycopg2 connection object (autocommit=False by default).
    """
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5433")
    dbname = os.getenv("POSTGRES_DB", "soil_platform")
    user = os.getenv("POSTGRES_USER", "soil_user")
    password = os.getenv("POSTGRES_PASSWORD", "")

    try:
        conn = psycopg2.connect(
            host=host,
            port=int(port),
            dbname=dbname,
            user=user,
            password=password,
            connect_timeout=5,          # fail fast rather than hanging
            options="-c client_encoding=UTF8",  # ensure UTF-8 session
        )
        return conn
    except psycopg2.OperationalError as exc:
        # Log the full technical error server-side only.
        logger.error("Database connection failed: %s", exc)
        # Return a safe, credential-free message to the caller.
        raise RuntimeError(
            "Impossible de se connecter à la base de données. "
            "Vérifiez que le conteneur Docker est démarré (docker compose up -d)."
        ) from exc


def close_connection(conn):
    """Close a psycopg2 connection explicitly.

    Why not rely on garbage collection or a context manager?
    psycopg2's `with conn:` only manages the transaction (commit/rollback).
    It does not close the underlying TCP connection. Explicit close is safer
    and clearer for readers of this code.

    Args:
        conn: an open psycopg2 connection, or None (safe to call with None).
    """
    if conn is not None:
        try:
            conn.close()
        except Exception as exc:
            logger.warning("Error closing database connection: %s", exc)
