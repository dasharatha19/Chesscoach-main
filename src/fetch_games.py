# src/fetch_games.py

import os
import sys
import time
from pathlib import Path

import requests

RAW_PGN_DIR = Path("data/raw_pgn")
RAW_PGN_DIR.mkdir(parents=True, exist_ok=True)


def get_available_months(username: str) -> list:
    url     = f"https://api.chess.com/pub/player/{username}/games/archives"
    headers = {"User-Agent": "ChessCoachAI/1.0 contact@chesscoach.dev"}

    response = requests.get(url, headers=headers)

    if response.status_code == 404:
        raise ValueError(f"Chess.com user '{username}' not found.")
    if response.status_code != 200:
        raise ValueError(f"Error fetching archives: {response.status_code}")

    archives = response.json().get("archives", [])
    print(f"Found {len(archives)} months of games for {username}")
    return archives


def fetch_month_pgn(archive_url: str) -> str:
    headers = {"User-Agent": "ChessCoachAI/1.0 contact@chesscoach.dev"}
    pgn_url  = archive_url + "/pgn"

    response = requests.get(pgn_url, headers=headers)
    if response.status_code == 200:
        return response.text
    return ""


def fetch_all_games(username: str, last_n_months: int = 6) -> str:
    """
    Fetches games for any Chess.com username.
    Returns combined PGN text.
    Raises ValueError if username not found.
    """
    print(f"Fetching games for: {username}")

    archives        = get_available_months(username)
    recent_archives = archives[-last_n_months:]
    print(f"Downloading last {len(recent_archives)} months...")

    all_pgn = ""

    for archive_url in recent_archives:
        parts       = archive_url.split("/")
        year, month = parts[-2], parts[-1]
        print(f"  Fetching {year}/{month}...", end=" ")

        pgn        = fetch_month_pgn(archive_url)
        game_count = pgn.count("[Event ")
        print(f"{game_count} games")

        all_pgn += pgn + "\n"
        time.sleep(0.5)

    return all_pgn


def save_games(pgn_text: str, username: str) -> Path:
    output_path = RAW_PGN_DIR / f"{username}_games.pgn"
    output_path.write_text(pgn_text, encoding="utf-8")
    return output_path


# ── Run directly ───────────────────────────────────────────────────────
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    username = os.getenv("CHESSCOM_USERNAME")

    if not username:
        print("ERROR: CHESSCOM_USERNAME not set in .env")
        sys.exit(1)

    pgn_text = fetch_all_games(username, last_n_months=6)

    if pgn_text:
        path  = save_games(pgn_text, username)
        total = pgn_text.count("[Event ")
        print(f"\n✅ Downloaded {total} games → saved to {path}")
    else:
        print("❌ No games downloaded. Double-check your username.")