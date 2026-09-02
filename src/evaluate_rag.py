# src/evaluate_rag.py
# Custom RAG evaluation — no ragas dependency needed
# Measures the same things: faithfulness, relevancy, context quality

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

sys.path.append(str(Path(__file__).parent))
from retriever import ask_groq, build_context, get_clients, retrieve_relevant_chunks
from router import GROQ_MODEL

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Which user's data to evaluate against. The eval questions/references
# below were written assuming a specific test user's game history
# (e.g. "Vienna Game, 76% win rate, 17 games" is THAT user's real stats,
# not a universal truth) — so this MUST match whichever username you
# actually ran /setup for. Change this before running eval against a
# different user's collection.
EVAL_USERNAME = os.getenv("CHESSCOM_USERNAME", "dasharatha19")

TEST_QUESTIONS = [
    {
        "question": "What is my biggest weakness in chess?",
        "reference": "endgame losses, Black pieces, specific openings"
    },
    {
        "question": "Which opening gives me the best win rate?",
        "reference": "Vienna Game, 76% win rate, 17 games"
    },
    {
        "question": "Do I perform better as White or Black?",
        "reference": "White vs Black comparison, win rates, game count"
    },
    {
        "question": "What openings do I play most often?",
        "reference": "Kings Pawn Opening 29 games, Vienna Game 17 games"
    },
]


def score_answer_with_llm(question, answer, context, reference, groq_client) -> dict:
    """
    Uses Groq itself as a judge to score our RAG answers.
    This is called LLM-as-judge evaluation — industry standard approach.
    """
    prompt = f"""You are evaluating a RAG system. Score these 3 metrics from 0.0 to 1.0.

QUESTION: {question}
REFERENCE (what a good answer should cover): {reference}
RETRIEVED CONTEXT (what was given to the AI): {context[:800]}
ACTUAL ANSWER: {answer}

Score these metrics:
1. faithfulness: Is the answer based on the retrieved context? (1.0 = fully grounded, 0.0 = hallucinated)
2. answer_relevancy: Does the answer address the question asked? (1.0 = perfectly relevant, 0.0 = off topic)
3. context_precision: Did the context contain what was needed to answer? (1.0 = perfect context, 0.0 = wrong context)

Respond ONLY with valid JSON like this exact format:
{{"faithfulness": 0.8, "answer_relevancy": 0.9, "context_precision": 0.7, "reason": "one sentence"}}"""

    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=200
    )

    raw = response.choices[0].message.content.strip()

    try:
        # parse JSON response
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        return json.loads(raw[start:end])
    except Exception: # noqa: BLE001 — LLM JSON output is unpredictable; fall back to neutral scores rather than crash the eval run
        return {"faithfulness": 0.5, "answer_relevancy": 0.5, "context_precision": 0.5, "reason": "parse error"}


def run_evaluation():
    print("\n" + "="*55)
    print("CHESSCOACH AI — RAG EVALUATION")
    print("="*55)

    from groq import Groq
    groq_client = Groq(api_key=GROQ_API_KEY)
    all_scores  = []

    for i, item in enumerate(TEST_QUESTIONS):
        question  = item["question"]
        reference = item["reference"]

        print(f"\nQ{i+1}: {question}")

        # get route and real context separately

        from retriever import get_aggregate_stats
        from router import classify_question

        qdrant, embed_model, groq_client_inner = get_clients()
        route = classify_question(question, groq_client)
        print(f"Route: {route}")

        # build real context the same way ask() does
        parts = []
        if route in ["aggregate", "hybrid"]:
            parts.append(get_aggregate_stats(EVAL_USERNAME))
        if route in ["specific", "hybrid"]:
            chunks = retrieve_relevant_chunks(question, EVAL_USERNAME, qdrant, embed_model, limit=4)
            parts.append(build_context(chunks))

        real_context = "\n\n".join(parts)

        # ✅ FIX 1: Generate the answer first before scoring
        try:
            answer = ask_groq(question, real_context, groq_client_inner, EVAL_USERNAME)
        except Exception: # noqa: BLE001 — one bad question must not abort the rest of the eval run
            answer = "error generating answer"
        print(f"Answer: {answer[:120]}...")

        # score with REAL answer + context
        try:
            scores = score_answer_with_llm(
                question, answer, real_context, reference, groq_client
            )
        except Exception as e:   # noqa: BLE001 — scorer call can fail in many ways; log and continue rather than abort the eval run
            print(f"Scorer error: {e}")
            scores = {
                "faithfulness": 0.5,
                "answer_relevancy": 0.5,
                "context_precision": 0.5,
                "reason": "scorer failed"
            }

        all_scores.append(scores)  # ← THIS LINE WAS MISSING

        print(f"Faithfulness      : {scores.get('faithfulness', 0):.2f}")
        print(f"Answer relevancy  : {scores.get('answer_relevancy', 0):.2f}")
        print(f"Context precision : {scores.get('context_precision', 0):.2f}")
        print(f"Reason            : {scores.get('reason', '')}")

    # Overall scores
    avg_f = sum(s.get("faithfulness", 0)     for s in all_scores) / len(all_scores)
    avg_r = sum(s.get("answer_relevancy", 0) for s in all_scores) / len(all_scores)
    avg_c = sum(s.get("context_precision", 0) for s in all_scores) / len(all_scores)
    overall = (avg_f + avg_r + avg_c) / 3

    print("\n" + "="*55)
    print("FINAL SCORES")
    print("="*55)
    print(f"Faithfulness      : {avg_f:.3f} /1.0")
    print(f"Answer relevancy  : {avg_r:.3f} /1.0")
    print(f"Context precision : {avg_c:.3f} /1.0")
    print(f"Overall           : {overall:.3f} /1.0")

    if overall >= 0.8:
        print("Grade: Excellent — production ready")
    elif overall >= 0.6:
        print("Grade: Good — minor improvements needed")
    else:
        print("Grade: Fair — needs more tuning")

    output = Path("data/processed/eval_results.json")
    with open(output, "w") as f:
        json.dump({"scores": all_scores, "averages": {
            "faithfulness": avg_f,
            "answer_relevancy": avg_r,
            "context_precision": avg_c,
            "overall": overall
        }}, f, indent=2)
    print(f"\nResults saved to {output}")


if __name__ == "__main__":
    run_evaluation()