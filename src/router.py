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
    Uses a tiny LLM call to classify the question type.
    Fast and cheap — we use a small model for routing.

    Examples:
    "Do I win more as White or Black?"   → aggregate
    "Why did I lose on 2025-03-10?"      → specific
    "What is my biggest weakness?"       → hybrid
    "Give me a study plan"               → hybrid
    """
    prompt = f"""Classify this chess question into exactly one category.

Question: {question}

Categories:
- aggregate: needs statistics across many games (win rates, totals, comparisons, "most often", "best", "worst", "overall", "weakness", "strength", "improve")
- specific: needs details from specific games (particular date, particular opening, particular opponent)
- hybrid: needs both statistics AND specific examples to answer well (study plan, detailed breakdown)

Reply with ONLY one word: aggregate, specific, or hybrid"""

    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=10      # we only need one word
    )

    route = response.choices[0].message.content.strip().lower()

    # safety fallback
    if route not in [ROUTE_AGGREGATE, ROUTE_SPECIFIC, ROUTE_HYBRID]:
        return ROUTE_HYBRID

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
        max_tokens=30
    )

    rewritten = response.choices[0].message.content.strip()
    print(f"Query rewritten: '{question}' → '{rewritten}'")
    return rewritten