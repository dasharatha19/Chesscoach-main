# src/chunker.py
#
# WHAT THIS FILE DOES:
# Takes the structured CSV (one row per game) and converts each game
# into "chunks" — small, meaningful text pieces that we can embed.
#
# WHY CHUNK?
# A vector database can't store a whole game at once meaningfully.
# We split each game into 3 chunks: opening, middlegame, endgame.
# This way when you ask "why do I blunder in endgames?" the retriever
# finds ENDGAME chunks specifically — not the whole game.

import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

USERNAME   = os.getenv("CHESSCOM_USERNAME")
PROCESSED  = Path("data/processed")


def game_to_chunks(row: dict) -> list[dict]:
    """
    Converts one game (one CSV row) into 3 chunk documents.
    Each chunk is a plain English description of that phase.
    
    Why plain English? Because our embedding model understands
    natural language better than raw chess moves like "e4 e5 Nf3".
    """
    base_meta = {
        "date":        row["date"],
        "played_as":   row["played_as"],
        "result":      row["result"],
        "opening":     row["opening"],
        "eco":         row["eco"],
        "my_rating":   row["my_rating"],
        "opp_rating":  row["opp_rating"],
        "time_control": row["time_control"],
        "termination": row["termination"],
        "total_moves": row["total_moves"],
    }

    chunks = []

    # ── CHUNK 1: Opening (moves 1-10) ─────────────────────────────────
    opening_text = f"""
Chess game opening phase. 
Player: {row['played_as']} pieces. 
Opening: {row['opening']} (ECO: {row['eco']}).
Result: {row['result']}.
My rating: {row['my_rating']}, Opponent rating: {row['opp_rating']}.
Time control: {row['time_control']}.
Opening moves: {row['opening_moves']}.
Date: {row['date']}.
""".strip()

    chunks.append({
        "text":  opening_text,
        "phase": "opening",
        **base_meta
    })

    # ── CHUNK 2: Middlegame (moves 11-30) ─────────────────────────────
    if row["middlegame_moves"]:
        middlegame_text = f"""
Chess game middlegame phase.
Player: {row['played_as']} pieces.
Opening that led here: {row['opening']}.
Result: {row['result']}.
My rating: {row['my_rating']}, Opponent rating: {row['opp_rating']}.
Middlegame moves: {row['middlegame_moves']}.
Game lasted {row['total_moves']} moves total.
Date: {row['date']}.
""".strip()

        chunks.append({
            "text":  middlegame_text,
            "phase": "middlegame",
            **base_meta
        })

    # ── CHUNK 3: Endgame (moves 31+) ──────────────────────────────────
    if row["endgame_moves"]:
        endgame_text = f"""
Chess game endgame phase.
Player: {row['played_as']} pieces.
Result: {row['result']}.
Termination: {row['termination']}.
My rating: {row['my_rating']}, Opponent rating: {row['opp_rating']}.
Endgame moves: {row['endgame_moves']}.
Game lasted {row['total_moves']} moves total.
Date: {row['date']}.
""".strip()

        chunks.append({
            "text":  endgame_text,
            "phase": "endgame",
            **base_meta
        })

    return chunks


def chunk_all_games(csv_path: Path) -> list[dict]:
    """
    Reads the full CSV and converts every game into chunks.
    Returns a flat list of all chunks across all games.
    """
    df = pd.read_csv(csv_path)
    df = df.fillna("")  # replace NaN with empty string

    all_chunks = []

    for _, row in df.iterrows():
        chunks = game_to_chunks(row.to_dict())
        all_chunks.extend(chunks)

    print(f"Created {len(all_chunks)} chunks from {len(df)} games")
    print(f"Avg chunks per game: {len(all_chunks)/len(df):.1f}")
    return all_chunks


# ── Run directly to test ───────────────────────────────────────────────
if __name__ == "__main__":
    csv_path = PROCESSED / f"{USERNAME}_games.csv"

    if not csv_path.exists():
        print(f"ERROR: {csv_path} not found. Run parse_pgn.py first.")
        sys.exit(1)

    chunks = chunk_all_games(csv_path)

    # Preview first 2 chunks so you can see what they look like
    print("\n── Sample chunk (opening) ──")
    print(chunks[0]["text"])
    # Find the first actual endgame chunk to preview
    endgame_chunks = [c for c in chunks if c["phase"] == "endgame"]
    if endgame_chunks:
        print("\n── Sample chunk (endgame) ──")
        print(endgame_chunks[0]["text"])
    else:
        print("\nNo endgame chunks found (short games only?)")
    print(f"\nTotal chunks ready for embedding: {len(chunks)}")