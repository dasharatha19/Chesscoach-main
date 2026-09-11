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
if SUPABASE_DB_URL:
    # Defensive strip — env vars pasted through a dashboard UI can
    # pick up invisible trailing whitespace/newlines that are genuinely
    # hard to spot by eye (copy-paste from a browser, chat interfaces
    # visually trimming what's actually stored, etc). Stripping here
    # means this can never cause a "database \"postgres\n\" does not
    # exist"-style error again, regardless of what's actually sitting
    # in Render's UI — permanent fix, not a one-time manual re-paste.
    SUPABASE_DB_URL = SUPABASE_DB_URL.strip()

DB_SCHEMA = os.getenv("DB_SCHEMA", "public")  # "prod" or "staging" —
# same Supabase project/connection URL is shared by both Render
# environments; THIS is what actually keeps them isolated from each
# other, by confining every query on this connection to one schema.
# Defaults to "public" (Postgres' default schema) if unset, so this
# doesn't break anything for local dev where isolation doesn't matter.


def get_db_connection():
    """
    Returns a new psycopg2 connection, scoped to DB_SCHEMA via
    search_path — every query on this connection only sees/affects
    that schema's tables, not any other environment's.
    Not cached/pooled yet — fine for current traffic levels (see
    ROADMAP.md Layer 11's WEB_CONCURRENCY discussion); worth revisiting
    with real connection pooling if load testing shows it's needed.
    """
    conn = psycopg2.connect(SUPABASE_DB_URL)
    with conn.cursor() as cur:
        cur.execute(f"SET search_path TO {DB_SCHEMA}, public")
    conn.commit()
    return conn


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