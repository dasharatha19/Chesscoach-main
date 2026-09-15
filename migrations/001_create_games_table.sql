-- migrations/001_create_games_table.sql
--
-- Run this ONCE, pasted whole into Supabase's SQL editor. It is
-- explicitly schema-qualified (prod.games / staging.games) rather
-- than relying on search_path — the SQL editor is a separate session
-- from your app's connections, with its own default search_path
-- (usually "public"), so an unqualified `CREATE TABLE games` here
-- would silently land in the wrong place and your app's DB_SCHEMA-
-- scoped queries would find nothing, ever, no error. Schema-qualifying
-- here removes that whole failure mode.
--
-- Column names match extract_game_data() in src/parse_pgn.py 1:1,
-- so get_games_df() in src/db.py can hand the result straight to
-- the same pandas logic get_aggregate_stats() already uses on the
-- CSV — no branching logic needed downstream of the DataFrame.

CREATE SCHEMA IF NOT EXISTS prod;
CREATE SCHEMA IF NOT EXISTS staging;

CREATE TABLE IF NOT EXISTS prod.games (
    id                BIGSERIAL PRIMARY KEY,
    username          TEXT NOT NULL,
    date              TEXT,
    played_as         TEXT,
    result            TEXT,
    opening           TEXT,
    eco               TEXT,
    my_rating         INT,
    opponent          TEXT,
    opp_rating        INT,
    my_accuracy       FLOAT,
    opp_accuracy      FLOAT,
    time_control      TEXT,
    termination       TEXT,
    opening_moves     TEXT,
    middlegame_moves  TEXT,
    endgame_moves     TEXT,
    total_moves       INT,
    inserted_at       TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS staging.games (
    id                BIGSERIAL PRIMARY KEY,
    username          TEXT NOT NULL,
    date              TEXT,
    played_as         TEXT,
    result            TEXT,
    opening           TEXT,
    eco               TEXT,
    my_rating         INT,
    opponent          TEXT,
    opp_rating        INT,
    my_accuracy       FLOAT,
    opp_accuracy      FLOAT,
    time_control      TEXT,
    termination       TEXT,
    opening_moves     TEXT,
    middlegame_moves  TEXT,
    endgame_moves     TEXT,
    total_moves       INT,
    inserted_at       TIMESTAMPTZ DEFAULT now()
);

-- Every query filters by username first — this is the one index
-- that actually matters at current scale, in both schemas.
CREATE INDEX IF NOT EXISTS idx_games_username ON prod.games(username);
CREATE INDEX IF NOT EXISTS idx_games_username ON staging.games(username);

-- NOTE: no unique/dedup key. There's no stable per-game ID in the
-- current PGN extraction (no Chess.com game URL/ID field pulled out
-- in extract_game_data()). insert_games() in db.py works around this
-- by deleting a user's existing rows before each insert, mirroring
-- how df.to_csv() already overwrites the whole CSV on every /setup
-- run — a "full refresh," not an incremental append. If you later
-- want incremental syncs, extract_game_data() needs to start pulling
-- Chess.com's game URL as a real unique key first.