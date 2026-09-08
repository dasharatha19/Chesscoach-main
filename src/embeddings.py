# src/embeddings.py
"""
Shared embedding function, used by BOTH embedder.py (indexing a user's
games during /setup) and retriever.py (embedding a user's question
during /ask). This is the ONE place in the whole app that talks to
Hugging Face's Inference API.

Why this exists: the embedding model used to be loaded locally via
fastembed/ONNX, in-process. That's what caused the Render OOM crash —
real model weights sitting in RAM inside a 512MB container, sometimes
loaded TWICE (embedder.py and retriever.py each kept their own copy).
Calling HF's Inference API instead means NO model weights are ever
loaded into this process's memory — a small HTTP request goes out,
HF's servers run the model, only the resulting vectors (small lists
of numbers) come back.

Trade-off, stated plainly: this adds real network latency per call
that a warmed local model wouldn't have. Batching (below) keeps this
reasonable for /setup's hundreds of chunks, but this should be timed
for real once deployed, not assumed fast.
"""

import os

import numpy as np
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

load_dotenv()

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
BATCH_SIZE = 32  # texts per HF API call, to avoid hundreds of individual round-trips

_client: InferenceClient | None = None


def _get_client() -> InferenceClient:
    global _client
    if _client is None:
        _client = InferenceClient(token=os.getenv("HF_TOKEN"))
    return _client


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Embed a batch of texts via HF's Inference API.
    Returns one 384-dim vector per input text, same order as input.
    """
    if not texts:
        return []

    client = _get_client()
    all_vectors: list[list[float]] = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        result = client.feature_extraction(batch, model=EMBEDDING_MODEL)
        all_vectors.extend(_to_sentence_vectors(result))

    return all_vectors


def embed_text(text: str) -> list[float]:
    """Embed a single text (e.g. one user question) — convenience wrapper."""
    return embed_texts([text])[0]


def _to_sentence_vectors(result) -> list[list[float]]:
    """
    HF's feature-extraction endpoint can come back in two different
    shapes depending on the model/backend:
      - 2D (n_texts, dim): already one vector per input text
      - 3D (n_texts, n_tokens, dim): token-level, needs mean-pooling
        into one vector per text
    Handled defensively rather than assuming one shape — this hasn't
    been exercised against the live API yet (no network access to
    huggingface.co from the environment this was written in), so
    testing this for real, against real data, is the next required
    step before trusting it in production.
    """
    arr = np.array(result)

    if arr.ndim == 2:
        return arr.tolist()
    elif arr.ndim == 3:
        return arr.mean(axis=1).tolist()
    else:
        raise ValueError(
            f"Unexpected embedding response shape {arr.shape} from HF "
            f"Inference API — expected 2D or 3D array."
        )