# app.py

import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.append(str(Path(__file__).parent / "src"))
from embedder import collection_exists, get_qdrant_client, setup_user
from retriever import ask

app = FastAPI(title="ChessCoach AI", version="2.0.1")

from fastapi import Request
from fastapi.responses import JSONResponse

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

@app.options("/{rest_of_path:path}")
async def preflight_handler(request: Request, rest_of_path: str):
    """Handle all OPTIONS preflight requests explicitly."""
    return JSONResponse(
        content={},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )

# Track which users are currently being set up
# so we don't run setup twice at the same time
setup_in_progress: set = set()


class QuestionRequest(BaseModel):
    question: str
    username: str


class AnswerResponse(BaseModel):
    answer:   str
    question: str
    username: str


class SetupResponse(BaseModel):
    username:     str
    total_games:  int
    total_chunks: int
    status:       str


@app.get("/")
def health_check():
    return {"status": "ChessCoach AI is running", "version": "2.0.0"}


@app.get("/check/{username}")
def check_user(username: str):
    """
    Check if a user's games are already indexed.
    Frontend calls this first to decide whether to show
    the setup screen or go straight to chat.
    """
    username = username.lower().strip()

    if username in setup_in_progress:
        return {"ready": False, "status": "setup_in_progress"}

    client = get_qdrant_client()
    ready  = collection_exists(client, username)

    # Also check CSV exists
    csv_path = Path("data/processed") / f"{username}_games.csv"
    if ready and csv_path.exists():
        import pandas as pd
        total_games = len(pd.read_csv(csv_path))
        return {"ready": True, "status": "ready", "total_games": total_games}

    return {"ready": False, "status": "not_setup"}


setup_results: dict = {}

@app.post("/setup/{username}")
async def setup_username(username: str):
    username = username.lower().strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username cannot be empty")
    if username in setup_in_progress:
        return {"status": "in_progress", "username": username}

    setup_in_progress.add(username)
    setup_results[username] = {"status": "in_progress"}

    def run_setup():
        try:
            result = setup_user(username)
            setup_results[username] = {"status": "ready", **result}
        except Exception as e: # # noqa: BLE001 — background thread; must catch anything so setup_results reports the failure instead of the thread dying silently  
            setup_results[username] = {"status": "error", "detail": str(e)}
        finally:
            setup_in_progress.discard(username)

    import threading
    thread = threading.Thread(target=run_setup, daemon=False)
    thread.start()
    return {"status": "started", "username": username}


@app.get("/setup-status/{username}")
def setup_status(username: str):
    username = username.lower().strip()
    if username in setup_results:
        return setup_results[username]
    return {"status": "not_started"}


@app.post("/ask", response_model=AnswerResponse)
def ask_question(request: QuestionRequest):
    """
    Main RAG endpoint — answers questions about a user's chess games.
    """
    username = request.username.lower().strip()

    if not username:
        raise HTTPException(status_code=400, detail="Username is required")

    # Make sure user is set up
    client = get_qdrant_client()
    if not collection_exists(client, username):
        raise HTTPException(
            status_code=404,
            detail=f"No data found for '{username}'. Call /setup/{username} first."
        )

    answer = ask(request.question, username)
    return AnswerResponse(
        answer=answer,
        question=request.question,
        username=username
    )


@app.get("/suggested-questions")
def suggested_questions():
    return {
        "questions": [
            "Why do I keep losing? What is my biggest weakness?",
            "Which opening should I stop playing?",
            "Do I perform better as White or Black?",
            "What patterns do you see in my endgame losses?",
            "Give me a personalized study plan for this week",
            "Which opponent type do I struggle against most?",
        ]
    }