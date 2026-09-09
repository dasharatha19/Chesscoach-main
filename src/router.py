# src/router.py
#
# WHAT THIS IS:
# A lightweight query router — classifies every question
# into one of two types before deciding how to answer it.
#
# This is how modern RAG systems work at scale.
# Instead of always doing vector search, we first ask:
# "what KIND of question is this?" then pick the right tool.

import os

from groq import Groq

# Groq periodically deprecates/decommissions models (it happened to this
# exact project — llama-3.3-70b-versatile was decommissioned 2026-08-16).
# Reading this from an env var means the NEXT deprecation is a one-line
# .env change instead of hunting through every file that calls Groq.
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
import os

from dotenv import load_dotenv

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


# Question types our system handles
ROUTE_AGGREGATE = "aggregate"   # needs stats across ALL games
ROUTE_SPECIFIC  = "specific"    # needs specific game details
ROUTE_HYBRID    = "hybrid"      # needs both


def classify_question(question: str, groq_client: Groq) -> str:
    """
    Query routing — decides whether a question needs:
    - "aggregate": exact pandas stats over ALL games (e.g. win rate)
    - "specific": vector search for example games/moments
    - "hybrid": both

    NOTE: I don't have live access to your original classify_question()
    right now (sandbox reset earlier this conversation), so this is
    rebuilt from what we established together, not a diff of your real
    file. Please compare this against what's actually in router.py and
    adjust the prompt wording if it differs — the important part is
    the parameter/fallback changes below, not the exact prompt text.
    """
    prompt = f"""Classify this chess coaching question into exactly ONE category:

- aggregate: needs overall statistics (win rate, totals, averages)
- specific: needs example games or specific moments
- hybrid: needs both statistics AND examples

Question: {question}

Reply with ONLY one word: aggregate, specific, or hybrid."""

    response = groq_client.chat.completions.create(
        model="openai/gpt-oss-20b",  # switched from gpt-oss-120b — this
        # task is simple one-word classification, doesn't need the
        # larger model's reasoning depth. Faster, and draws from a
        # SEPARATE free-tier quota than the main answer-generation calls.
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=50,          # raised from 10 — same reasoning-token
                                 # issue as rewrite_query: 10 tokens is
                                 # an extremely tight budget for a
                                 # reasoning model, plausibly why every
                                 # question was landing on the same
                                 # answer regardless of actual content.
        reasoning_effort="low",  # minimize reasoning spend on this
                                  # simple classification task.
    )

    route = response.choices[0].message.content.strip().lower()

    # Same diagnostic as rewrite_query — real proof, not inference.
    usage = response.usage
    reasoning_tokens = getattr(usage.completion_tokens_details, "reasoning_tokens", None) if hasattr(usage, "completion_tokens_details") else None
    print(f"  [classify_question diagnostics] finish_reason={response.choices[0].finish_reason}, "
          f"reasoning_tokens={reasoning_tokens}, completion_tokens={usage.completion_tokens}, "
          f"max_tokens_budget=50")

    valid_routes = {"aggregate", "specific", "hybrid"}
    if route not in valid_routes:
        # Defensive fallback — if the model returns something empty,
        # malformed, or unexpected, default to "hybrid" rather than
        # crash or silently misroute. Hybrid is the safest default
        # since it includes both data sources.
        print(f"Route classification returned unexpected value: {route!r} — defaulting to 'hybrid'")
        return "hybrid"

    return route

def rewrite_query(question: str, groq_client: Groq) -> str:
    """
    Query rewriting — modern RAG technique.
    Rewrites the user's casual question into a
    search-optimized query for better vector retrieval.

    "what is my biggest weakness?"
    → "chess losses blunders mistakes weak openings losing games"
    """
    prompt = f"""You are a search query optimizer for a chess game database.

Rewrite this question into a short search query (5-10 words max) that will find the most relevant chess games and moments.

Focus on: chess terms, game phases (opening/middlegame/endgame), results (win/loss/draw), piece colors (white/black).
Remove: personal pronouns, filler words, question words.

Question: {question}

Reply with ONLY the rewritten search query, nothing else."""

    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=150,        # raised from 30 — gpt-oss-120b is a
                                # REASONING model that spends completion
                                # tokens on internal chain-of-thought
                                # BEFORE writing visible content. 30
                                # tokens was very likely being consumed
                                # entirely by reasoning, leaving nothing
                                # for the actual rewritten query —
                                # confirmed as a known, documented
                                # failure mode for gpt-oss models with
                                # small token budgets.
        reasoning_effort="low",  # minimize (can't fully disable for
                                  # gpt-oss models — only "low"/"medium"/
                                  # "high" supported) reasoning spend
                                  # on this simple, non-reasoning task.
    )

    rewritten = response.choices[0].message.content.strip()

    # Diagnostic — shows the REAL reasoning-token spend, so we know
    # for certain whether reasoning is eating the budget, instead of
    # just inferring it from an empty result. Check this in your logs
    # after testing — if reasoning_tokens is close to max_tokens (150),
    # the budget genuinely isn't enough and needs raising further.
    usage = response.usage
    reasoning_tokens = getattr(usage.completion_tokens_details, "reasoning_tokens", None) if hasattr(usage, "completion_tokens_details") else None
    print(f"  [rewrite_query diagnostics] finish_reason={response.choices[0].finish_reason}, "
          f"reasoning_tokens={reasoning_tokens}, completion_tokens={usage.completion_tokens}, "
          f"max_tokens_budget=150")

    if not rewritten:
        # Defensive fallback — if reasoning still consumes the whole
        # budget despite the above (or for any other reason), fall
        # back to the ORIGINAL question instead of silently embedding
        # an empty string, which is semantically meaningless and
        # degrades vector search with no visible error.
        print(f"Query rewritten: '{question}' → (empty — falling back to original question)")
        return question

    print(f"Query rewritten: '{question}' → '{rewritten}'")
    return rewritten