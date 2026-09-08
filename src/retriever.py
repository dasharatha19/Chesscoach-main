# src/retriever.py

import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from groq import Groq
from qdrant_client import QdrantClient

load_dotenv()

sys.path.append(str(Path(__file__).parent))
from embeddings import embed_text  # shared HF Inference API embedding call
from router import GROQ_MODEL  # single source of truth for which Groq model to use

ROUTE_AGGREGATE = "aggregate"
ROUTE_SPECIFIC  = "specific"
ROUTE_HYBRID    = "hybrid"

GROQ_API_KEY    = os.getenv("GROQ_API_KEY")
PROCESSED       = Path("data/processed")


def get_collection_name(username: str) -> str:
    return f"chess_{username.lower()}"


# Module-level cache — Qdrant/Groq clients get created ONCE, the first
# time get_clients() runs, then reused for every subsequent call.
# The embedding model itself is no longer part of this at all — since
# switching to HF's Inference API (see embeddings.py), there's no
# local model to load or cache; every embed call goes out over the
# network instead of holding weights in this process's memory.
_cached_clients = None


def get_clients():
    global _cached_clients
    if _cached_clients is None:
        qdrant = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY")
        )
        groq  = Groq(api_key=GROQ_API_KEY)
        _cached_clients = (qdrant, groq)
    return _cached_clients


def get_aggregate_stats(username: str) -> str:
    csv_path = PROCESSED / f"{username}_games.csv"

    # If CSV missing (Render restarted), regenerate it from Chess.com
    if not csv_path.exists():
        print(f"CSV missing for {username} — regenerating...")
        from fetch_games import fetch_all_games, save_games
        from parse_pgn import parse_pgn_file
        pgn_text = fetch_all_games(username, last_n_months=6)
        pgn_path = save_games(pgn_text, username)
        df = parse_pgn_file(pgn_path, username)
        PROCESSED.mkdir(parents=True, exist_ok=True)
        df.to_csv(csv_path, index=False)
    else:
        df = pd.read_csv(csv_path)

    total  = len(df)
    wins   = len(df[df["result"] == "win"])
    losses = len(df[df["result"] == "loss"])
    draws  = len(df[df["result"] == "draw"])

    white_df   = df[df["played_as"] == "white"]
    black_df   = df[df["played_as"] == "black"]
    white_wins = len(white_df[white_df["result"] == "win"])
    black_wins = len(black_df[black_df["result"] == "win"])

    top_openings = df.groupby("opening").agg(
        games=("result", "count"),
        wins=("result", lambda x: (x == "win").sum())
    ).sort_values("games", ascending=False).head(8)

    top_openings["win_rate"] = (
        top_openings["wins"] / top_openings["games"] * 100
    ).round(1)

    openings_text = "\n".join([
        f"  {row.Index[:40]}: {row.games} games, {row.win_rate}% wins"
        for row in top_openings.itertuples()
    ])

    return f"""FULL GAME STATISTICS (all {total} games):
Wins: {wins} ({100*wins//total}%)
Losses: {losses} ({100*losses//total}%)
Draws: {draws} ({100*draws//total}%)

As White: {len(white_df)} games, {white_wins} wins ({100*white_wins//len(white_df)}%)
As Black: {len(black_df)} games, {black_wins} wins ({100*black_wins//len(black_df)}%)

Top openings by games played:
{openings_text}"""


def retrieve_relevant_chunks(
    question: str,
    username: str,
    qdrant: QdrantClient,
    limit: int = 8
) -> list[dict]:
    query_vector = embed_text(question)  # via HF Inference API
    collection   = get_collection_name(username)

    results = qdrant.query_points(
        collection_name=collection,
        query=query_vector,
        limit=limit
    ).points

    return [r.payload for r in results]


def build_context(chunks: list[dict]) -> str:
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(f"\nGame {i}:\n{chunk['text']}\n---")
    return "\n".join(context_parts)


def ask_groq(question: str, context: str, groq_client: Groq, username: str) -> str:
    system_prompt = f"""You are ChessCoach AI — a personalized chess improvement assistant.

You have been given real game data from {username}'s chess history on Chess.com.
Each game shows the phase (opening/middlegame/endgame), result (win/loss/draw),
opening name, rating, and moves played.

Your job:
- Analyze ONLY the game data provided below — never reference games not shown
- Never say "Game 1", "Game 2" etc — you don't have numbered games, only chunks
- Mention specific openings, dates, and results you can see in the context
- Never invent statistics or games not present in the retrieved chunks
- If you only see a few games in context, say "based on the games I can see" — never extrapolate
- Never mention an opening name unless it appears explicitly in the context below
- If you cannot answer confidently from the context, say so honestly
- NEVER mention a specific game, move, or opening that is not explicitly written in the context below. If it is not there, do not say it.
- When OVERALL STATISTICS are provided, use ONLY those for win rates and opening names. NEVER mix opening names from SPECIFIC RELEVANT GAMES into statistical claims.
- Be direct and actionable — tell them exactly what to work on
- Keep your ENTIRE answer under 180 words. This is a hard limit, not a suggestion.
- Structure your answer as at most 2 short paragraphs (or one short paragraph + a brief list).
- ALWAYS finish with a complete sentence. Never stop mid-word or mid-thought — if you're running long, wrap up early rather than being cut off.

Remember: You are analyzing REAL games from their history, not hypothetical scenarios."""

    user_message = f"""Here are the most relevant games from my chess history:

{context}

My question: {question}

IMPORTANT: Only reference openings and games explicitly shown above. Do not invent or extrapolate."""

    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message}
        ],
        temperature=0.1,
        max_tokens=650   # safety margin above the ~180-word target above —
                          # NOT the fix itself. The prompt instruction is the
                          # real fix; this just prevents a mid-sentence cutoff
                          # if the model slightly overruns anyway.
    )

    return response.choices[0].message.content


def ask(question: str, username: str) -> str:
    """
    Full RAG pipeline for a specific user.
    """
    from router import classify_question, rewrite_query

    qdrant, groq_client = get_clients()

    route = classify_question(question, groq_client)
    print(f"Route: {route}")

    stats       = ""
    context     = ""
    total_games = 0

    if route == ROUTE_AGGREGATE or route == ROUTE_HYBRID:
        stats       = get_aggregate_stats(username)
        csv_path    = PROCESSED / f"{username}_games.csv"
        total_games = len(pd.read_csv(csv_path))
        print("Used: CSV aggregate stats")

    if route == ROUTE_SPECIFIC or route == ROUTE_HYBRID:
        search_query = rewrite_query(question, groq_client)
        chunks       = retrieve_relevant_chunks(
            search_query, username, qdrant, limit=4
        )
        context = build_context(chunks)
        print("Used: vector search with rewritten query")

    parts = []
    if stats:
        parts.append(f"=== OVERALL STATISTICS (all {total_games} games) ===\n{stats}")
    if context:
        parts.append(
            f"=== SPECIFIC RELEVANT GAMES (examples only — do NOT use opening names from here for statistics) ===\n{context}"
        )

    full_context = "\n\n".join(parts)
    return ask_groq(question, full_context, groq_client, username)