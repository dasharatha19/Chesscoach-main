# src/embedder.py

import os
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

sys.path.append(str(Path(__file__).parent))
from chunker import chunk_all_games

load_dotenv()

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
PROCESSED       = Path("data/processed")


def get_collection_name(username: str) -> str:
    """Each user gets their own Qdrant collection."""
    return f"chess_{username.lower()}"


def get_qdrant_client() -> QdrantClient:
    return QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY")
    )


def get_embedding_model() -> TextEmbedding:
    return TextEmbedding(EMBEDDING_MODEL)


def collection_exists(client: QdrantClient, username: str) -> bool:
    existing = [c.name for c in client.get_collections().collections]
    return get_collection_name(username) in existing


def create_collection(client: QdrantClient, username: str):
    collection_name = get_collection_name(username)
    existing        = [c.name for c in client.get_collections().collections]

    if collection_name in existing:
        # Check if it already has vectors — don't wipe good data!
        count = client.count(collection_name=collection_name).count
        if count > 0:
            print(f"Collection '{collection_name}' already has {count} vectors — skipping")
            return
        print(f"Collection '{collection_name}' exists but empty — recreating")
        client.delete_collection(collection_name)

    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE)
    )
    print(f"Created collection: {collection_name}")


def embed_and_store(chunks: list[dict], client: QdrantClient,
                    model: TextEmbedding, username: str):
    collection_name = get_collection_name(username)
    print(f"Embedding {len(chunks)} chunks...")

    texts      = [chunk["text"] for chunk in chunks]
    embeddings = list(model.embed(texts))

    points = []
    for chunk, embedding in zip(chunks, embeddings):
        points.append(PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding.tolist(),
            payload={
                "text":         chunk["text"],
                "phase":        chunk["phase"],
                "result":       chunk["result"],
                "opening":      chunk["opening"],
                "played_as":    chunk["played_as"],
                "my_rating":    chunk["my_rating"],
                "opp_rating":   chunk["opp_rating"],
                "date":         chunk["date"],
                "termination":  chunk["termination"],
                "total_moves":  chunk["total_moves"],
                "time_control": chunk["time_control"],
            }
        ))

    batch_size = 100
    for i in range(0, len(points), batch_size):
        batch = points[i:i + batch_size]
        client.upsert(collection_name=collection_name, points=batch)
        print(f"  Stored {min(i + batch_size, len(points))}/{len(points)} chunks...")

    print(f"All {len(points)} chunks stored for {username}!")


def setup_user(username: str) -> dict:
    """
    Full pipeline for a new user:
    fetch → parse → chunk → embed
    Returns stats dict.
    """
    from fetch_games import fetch_all_games, save_games
    from parse_pgn import parse_pgn_file

    # Step 1: Fetch games
    print(f"\n[1/4] Fetching games for {username}...")
    pgn_text = fetch_all_games(username, last_n_months=6)
    if not pgn_text or pgn_text.count("[Event ") == 0:
        raise ValueError(f"No games found for '{username}' on Chess.com")

    pgn_path = save_games(pgn_text, username)
    total_games = pgn_text.count("[Event ")
    print(f"Downloaded {total_games} games")

    # Step 2: Parse PGN → CSV
    print("\n[2/4] Parsing games...")
    df       = parse_pgn_file(pgn_path, username)
    csv_path = PROCESSED / f"{username}_games.csv"
    PROCESSED.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False)
    print(f"Parsed {len(df)} games")

    # Step 3: Chunk
    print("\n[3/4] Chunking games...")
    chunks = chunk_all_games(csv_path)

    # Step 4: Embed + store
    print("\n[4/4] Embedding and storing in Qdrant...")
    client = get_qdrant_client()
    model  = get_embedding_model()
    create_collection(client, username)
    embed_and_store(chunks, client, model, username)

    return {
        "username":    username,
        "total_games": len(df),
        "total_chunks": len(chunks),
        "collection":  get_collection_name(username)
    }


# ── Run directly ───────────────────────────────────────────────────────
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    import os
    username = os.getenv("CHESSCOM_USERNAME")
    result   = setup_user(username)
    print(f"\n✅ Setup complete: {result}")