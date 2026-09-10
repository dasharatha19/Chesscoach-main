# src/db.py
"""
Shared Postgres (Supabase) connection — used wherever the app needs
structured, persistent game data instead of the old ephemeral local
CSV. Kept as its own small module, same pattern as embeddings.py for
HF — one shared place for one external dependency.
"""

import os

import psycopg2
from dotenv import load_dotenv

load_dotenv()

SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")


def get_db_connection():
    """
    Returns a new psycopg2 connection. Not cached/pooled yet — fine
    for current traffic levels (see ROADMAP.md Layer 11's WEB_CONCURRENCY
    discussion); worth revisiting with real connection pooling if/when
    load testing shows this is a bottleneck.
    """
    return psycopg2.connect(SUPABASE_DB_URL)


def check_db_connection() -> bool:
    """
    Lightweight reachability check — SELECT 1, nothing schema-specific.
    Used by /ready and /health/db so those checks work regardless of
    which tables actually exist yet.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        return True
    finally:
        conn.close()
