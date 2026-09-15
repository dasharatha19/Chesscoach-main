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


# ── games table — write/read path ───────────────────────────────────
#
# Postgres is the primary path; the CSV written alongside it in
# embedder.py's setup_user() is the fallback if Supabase is ever
# unreachable — see get_games_df() below and get_aggregate_stats()
# in retriever.py, which tries this first and falls back to CSV on
# any exception here.

_GAMES_COLUMNS = [
    "username", "date", "played_as", "result", "opening", "eco",
    "my_rating", "opponent", "opp_rating", "my_accuracy", "opp_accuracy",
    "time_control", "termination", "opening_moves", "middlegame_moves",
    "endgame_moves", "total_moves",
]


def insert_games(username: str, df) -> int:
    """
    Replaces all stored rows for this user with the current DataFrame.
    There's no stable per-game ID coming out of parse_pgn.py yet (see
    migrations/001_create_games_table.sql), so this mirrors the CSV's
    existing behavior — df.to_csv() overwrites the whole file on every
    /setup run — rather than trying to dedupe/append. A re-run here
    means "fresh full refresh," same as the CSV.
    """
    import pandas as pd

    rows = [
        (
            username, r.date, r.played_as, r.result, r.opening, r.eco,
            int(r.my_rating), r.opponent, int(r.opp_rating),
            None if pd.isna(r.my_accuracy) else float(r.my_accuracy),
            None if pd.isna(r.opp_accuracy) else float(r.opp_accuracy),
            r.time_control, r.termination, r.opening_moves,
            r.middlegame_moves, r.endgame_moves, int(r.total_moves),
        )
        for r in df.itertuples(index=False)
    ]

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM games WHERE username = %s", (username,))
            if rows:
                placeholders = ",".join(["%s"] * len(_GAMES_COLUMNS))
                cur.executemany(
                    f"INSERT INTO games ({','.join(_GAMES_COLUMNS)}) "
                    f"VALUES ({placeholders})",
                    rows,
                )
        conn.commit()
        return len(rows)
    finally:
        conn.close()


def get_games_df(username: str):
    """
    Reads this user's games back out of Postgres as a DataFrame with
    the same columns parse_pgn.py produces from the CSV — so
    get_aggregate_stats() can run identical pandas logic regardless of
    which source it came from. Raises if Postgres has no rows for this
    user (including "the table doesn't exist yet"), which is exactly
    the signal retriever.py's fallback needs to drop to the CSV.
    """
    import pandas as pd

    conn = get_db_connection()
    try:
        df = pd.read_sql(
            "SELECT * FROM games WHERE username = %s ORDER BY id",
            conn,
            params=(username,),
        )
    finally:
        conn.close()

    if df.empty:
        raise ValueError(f"No Postgres rows for '{username}' yet")
    return df