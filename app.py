# app.py

import os
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.append(str(Path(__file__).parent / "src"))

from embedder import collection_exists, get_qdrant_client, setup_user
from retriever import ask

# Single source of truth for the version number. Originally this read
# pyproject.toml directly as a file at runtime — but that broke on
# Render: the raw source file isn't guaranteed to sit next to app.py
# inside the deployed container, even though it's right there locally.
# importlib.metadata reads the version from the package's INSTALLED
# metadata instead (created when `pip install -e .` / `uv sync` runs),
# which exists regardless of whether the original .toml file is
# physically present at runtime — the correct, deploy-environment-safe
# way to do this.
try:
    APP_VERSION = version("chesscoach-ai")
except PackageNotFoundError:
    # Fallback so the app still starts even if something's unusual
    # about how it was installed — never let a version lookup crash
    # the whole app the way the old file-read approach just did.
    APP_VERSION = "0.0.0-unknown"

app = FastAPI(title="ChessCoach AI", version=APP_VERSION)

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
@app.head("/")  # UptimeRobot (and most uptime monitors) ping with HEAD,
                 # not GET, to save bandwidth — without this, every ping
                 # got a 405 even though the app was genuinely healthy.
def health_check():
    return {"status": "ChessCoach AI is running", "version": APP_VERSION}


@app.get("/health")
@app.head("/health")
def health():
    """
    LIVENESS check — "is the process itself alive and responding?"
    Deliberately does ZERO real work: no DB calls, no external calls.
    If this ever gets slow, something is badly wrong with the process
    itself, not with a dependency — that distinction is the whole
    point of keeping this separate from /ready below.
    Kept as a separate route from "/" (which stays, for backward
    compatibility with anything already pointed at it) since "/health"
    is the more conventional/expected name for monitoring tools.
    """
    return {"status": "alive"}


@app.get("/ready")
def ready():
    """
    READINESS check — "is the app not just alive, but actually able
    to serve real traffic right now?" Checks the things /ask and
    /setup actually depend on. Returns 503 (not 200) if anything
    required is missing/unreachable, so monitoring tools and load
    balancers can correctly tell "up but broken" apart from "up and
    working" — a plain 200 from "/" can't make that distinction.
    """
    checks = {}
    all_ok = True

    # Required env vars actually present? (root cause of the earlier
    # "Connection refused" Qdrant bug was exactly this, silently)
    for var in ("QDRANT_URL", "QDRANT_API_KEY", "GROQ_API_KEY"):
        present = bool(os.getenv(var))
        checks[f"env:{var}"] = "ok" if present else "MISSING"
        if not present:
            all_ok = False

    # Can we actually reach Qdrant right now, not just "is the URL set"?
    try:
        client = get_qdrant_client()
        client.get_collections()
        checks["qdrant_connection"] = "ok"
    except Exception as e:  # noqa: BLE001 — intentionally broad: this
        # health check's whole job is "catch ANY failure reaching Qdrant",
        # not just one specific exception type.
        checks["qdrant_connection"] = f"FAILED: {e}"
        all_ok = False

    status_code = 200 if all_ok else 503
    return JSONResponse(
        status_code=status_code,
        content={"ready": all_ok, "checks": checks}
    )


@app.get("/health/db")
def health_db():
    """
    Dependency-specific check — narrows down "which piece is actually
    broken" faster than reading a full traceback. Checks ONLY Qdrant,
    directly, and reports latency so slow-but-technically-working
    counts differently from fully down.
    """
    import time
    start = time.monotonic()
    try:
        client = get_qdrant_client()
        collections = client.get_collections()
        latency_ms = round((time.monotonic() - start) * 1000, 1)
        return {
            "status": "ok",
            "latency_ms": latency_ms,
            "collection_count": len(collections.collections),
        }
    except Exception as e:  # noqa: BLE001 — same reasoning as /ready above
        latency_ms = round((time.monotonic() - start) * 1000, 1)
        return JSONResponse(
            status_code=503,
            content={"status": "unreachable", "latency_ms": latency_ms, "error": str(e)}
        )


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
async def setup_username(username: str, background_tasks: BackgroundTasks):
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
        except Exception as e:  # noqa: BLE001 — this runs in a background
            # thread with no caller waiting synchronously; if this doesn't
            # catch everything, the thread dies silently and /setup-status
            # would poll forever with no way to ever report the failure.
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
    """
    Fetches, parses, chunks, and embeds games for a new user.
    This takes ~30-60 seconds depending on game count.
    """
    username = username.lower().strip()

    if not username:
        raise HTTPException(status_code=400, detail="Username cannot be empty")

    if username in setup_in_progress:
        raise HTTPException(status_code=409, detail="Setup already in progress for this user")

    setup_in_progress.add(username)

    try:
        result = setup_user(username)
        return SetupResponse(
            username=result["username"],
            total_games=result["total_games"],
            total_chunks=result["total_chunks"],
            status="ready"
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:  # noqa: BLE001 — top-level API error boundary:
        # anything unexpected here should become a proper 500 response,
        # not an unhandled crash leaking a raw traceback to the caller.
        raise HTTPException(status_code=500, detail=f"Setup failed: {e!s}")
    finally:
        setup_in_progress.discard(username)


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