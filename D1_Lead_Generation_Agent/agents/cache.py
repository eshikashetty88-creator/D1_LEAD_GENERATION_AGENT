import hashlib
import json
import sqlite3
import time
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent.parent / "cache" / "pipeline_cache.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cache (
            cache_key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            created_at REAL NOT NULL
        )
        """
    )
    return conn


def make_key(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


def get_cached(prefix: str, value: str, ttl_hours: float = 24):
    key = make_key(prefix, value)
    with _connect() as conn:
        row = conn.execute(
            "SELECT value, created_at FROM cache WHERE cache_key = ?",
            (key,),
        ).fetchone()

    if not row:
        return None

    if time.time() - row[1] > ttl_hours * 3600:
        return None

    return json.loads(row[0])


def set_cached(prefix: str, value: str, data):
    key = make_key(prefix, value)
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO cache(cache_key, value, created_at) VALUES (?, ?, ?)",
            (key, json.dumps(data), time.time()),
        )
