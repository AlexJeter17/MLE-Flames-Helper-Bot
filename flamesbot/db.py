"""Read-only access to the MLE Postgres database.

Read-only is enforced in three layers:
  1. Every session sets default_transaction_read_only=on and psycopg's
     connection.read_only, so the server rejects any write.
  2. The session verifies transaction_read_only is actually 'on' before use.
  3. Every query passes a guard that only allows a single SELECT/WITH statement
     with no write keywords, and values are always bound parameters.
"""
import logging
import re
from contextlib import contextmanager
from typing import Any, Iterator

import psycopg
from psycopg.conninfo import conninfo_to_dict
from psycopg.rows import dict_row

import config

log = logging.getLogger(__name__)

_STARTS_WITH_READ = re.compile(r"^\s*(select|with)\b", re.IGNORECASE)
_WRITE_KEYWORDS = re.compile(
    r"\b(insert|update|delete|merge|upsert|truncate|alter|drop|create|grant|revoke"
    r"|copy|call|do|vacuum|reindex|cluster|lock|comment|refresh|set|reset)\b",
    re.IGNORECASE,
)


class ReadOnlyViolation(RuntimeError):
    """Raised when code tries to run anything other than a single SELECT."""


class DatabaseNotConfigured(RuntimeError):
    pass


def _check_sql(sql: str) -> None:
    body = sql.strip().rstrip(";")
    if not _STARTS_WITH_READ.match(body):
        raise ReadOnlyViolation("Only SELECT queries are allowed.")
    if ";" in body:
        raise ReadOnlyViolation("Multiple statements are not allowed.")
    if _WRITE_KEYWORDS.search(body):
        raise ReadOnlyViolation("Query contains a write keyword.")


def _connect() -> psycopg.Connection:
    if not config.DB_CONNSTRING:
        raise DatabaseNotConfigured("connstring is not set in .env")

    params = conninfo_to_dict(config.DB_CONNSTRING)
    if config.DB_SSL_ROOT_CERT.is_file():
        # verify-ca: encrypted + server cert must chain to the DO CA.
        # (verify-full fails because DO's cert is issued for an IP SAN.)
        params.update(sslmode="verify-ca", sslrootcert=str(config.DB_SSL_ROOT_CERT))
    else:
        log.warning("CA certificate %s not found; falling back to sslmode=require",
                    config.DB_SSL_ROOT_CERT.name)
        params["sslmode"] = "require"

    params["options"] = (
        "-c default_transaction_read_only=on"
        f" -c statement_timeout={config.DB_STATEMENT_TIMEOUT_MS}"
        " -c TimeZone=UTC"
    )
    params.setdefault("connect_timeout", 15)

    conn = psycopg.connect(**params, row_factory=dict_row)
    conn.read_only = True
    return conn


class ReadOnlySession:
    def __init__(self, conn: psycopg.Connection):
        self._conn = conn

    def fetch_all(self, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        _check_sql(sql)
        with self._conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()

    def fetch_one(self, sql: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        rows = self.fetch_all(sql, params)
        return rows[0] if rows else None


@contextmanager
def session() -> Iterator[ReadOnlySession]:
    """Open a short-lived read-only connection. Always rolled back and closed."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SHOW transaction_read_only")
            if cur.fetchone()["transaction_read_only"] != "on":
                raise ReadOnlyViolation("Database session is not read-only; refusing to continue.")
        yield ReadOnlySession(conn)
    finally:
        try:
            conn.rollback()
        finally:
            conn.close()
