# ♟ ChessCoach AI

> A personalized chess improvement system that analyzes your game history, detects your weakness patterns, and recommends exactly what to study — powered by RAG + LLM.

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-modern-green?style=flat-square&logo=fastapi)
![Qdrant](https://img.shields.io/badge/Qdrant-vector%20db-purple?style=flat-square)
![Groq](https://img.shields.io/badge/Groq-LLM-orange?style=flat-square)
![Chess.com](https://img.shields.io/badge/Chess.com-API-lightgrey?style=flat-square)

---

## What is this?

Most chess tools give you engine analysis — cold numbers and arrows. **ChessCoach AI** does something different:

- Connects to your **Chess.com game history** via the public API
- Analyzes **patterns across hundreds of your games**
- Finds your **specific weaknesses** (not generic advice)
- Answers questions like *"Why do I keep losing as Black?"* with data-backed, personalized explanations
- Generates a **personalized weekly study plan** based on your actual weak spots

---

## The RAG Pipeline

```
Chess.com API
      ↓
fetch_games.py     →  pulls your game history as PGN files
      ↓
parse_pgn.py       →  extracts structured data (opening, result, accuracy, moves)
      ↓
chunker.py         →  splits each game into Opening / Middlegame / Endgame segments
      ↓
embedder.py        →  converts chunks to vectors using fastembed
      ↓
Qdrant             →  stores and indexes all vectors locally
      ↓
retriever.py       →  finds relevant game moments for any question
      ↓
Groq LLM           →  generates personalized, specific answers
      ↓
FastAPI + Next.js  →  clean chat UI
```

---

## Tech Stack

| Layer | Tool | Why |
|---|---|---|
| Package manager | `uv` | Fast, modern Python tooling |
| Chess parsing | `python-chess` | Industry standard PGN library |
| Data source | Chess.com PubAPI | Free, no auth needed |
| RAG framework | `LangChain` | Pipeline orchestration |
| Embeddings | `fastembed` | Free, no API key needed |
| Vector DB | `Qdrant` | Modern, fast, runs locally |
| LLM | `Groq` | Free tier, blazing fast inference |
| Backend | `FastAPI` | Modern async Python API |
| Frontend | `Next.js` | React-based production UI |

---

## Project Structure

```
chesscoach-ai/
│
├── src/
│   ├── fetch_games.py      # Phase 1: Pull games from Chess.com API
│   ├── parse_pgn.py        # Phase 2: Parse PGN → structured CSV
│   ├── chunker.py          # Phase 2: Split games into RAG chunks
│   ├── embedder.py         # Phase 3: Embed chunks → Qdrant
│   ├── retriever.py        # Phase 3: Semantic search over game history
│   ├── llm_chain.py        # Phase 3: Groq LLM + prompt logic
│   ├── analyzer.py         # Phase 4: Pattern detection across games
│   └── study_plan.py       # Phase 5: Personalized study plan generator
│
├── data/
│   ├── raw_pgn/            # Downloaded PGN files (gitignored)
│   └── processed/          # Structured CSVs (gitignored)
│
├── app.py                  # FastAPI backend entry point
├── pyproject.toml          # uv dependencies
├── .env.example            # Environment variable template
└── README.md
```

---

## Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/dashusujainx/chesscoach-ai.git
cd chesscoach-ai
```

### 2. Install dependencies

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
uv sync
```
             





             
### 3. Set up environment variables

```bash
cp .env.example .env
```

Edit `.env` with your values:

```env
CHESSCOM_USERNAME=your_chess_com_username
GROQ_API_KEY=your_groq_api_key
```

Get a free Groq API key at [console.groq.com](https://console.groq.com)

### 4. Fetch your games

```bash
uv run python src/fetch_games.py
```

### 5. Parse and analyze

```bash
uv run python src/parse_pgn.py
```

---

## Build Phases

| Phase | Status | What it does |
|---|---|---|
| Phase 1: Data Collection | ✅ Done | Fetch game history from Chess.com API |
| Phase 2: Parsing | ✅ Done | Extract structured data from PGN files |
| Phase 3: RAG Pipeline | 🔄 In Progress | Embed + store + retrieve game chunks |
| Phase 4: Pattern Analysis | ⏳ Upcoming | Detect weakness patterns across games |
| Phase 5: UI | ⏳ Upcoming | FastAPI backend + Next.js chat interface |
| Phase 6: Evaluation | ⏳ Upcoming | RAGAs scoring + deployment |

---

## Example Questions You Can Ask

Once fully built, you'll be able to ask:

- *"Why do I keep losing as Black?"*
- *"What's my worst opening and why?"*
- *"Do I blunder more in endgames or middlegames?"*
- *"Give me a study plan for this week based on my weaknesses"*
- *"How does my accuracy change when I'm low on time?"*

---

## What makes this different from just using ChatGPT?

ChatGPT has no access to your game history. It can only give generic chess advice.

ChessCoach AI has **your 276 games embedded in a vector database**. Every answer is grounded in your specific patterns — not generic theory.

| | Generic AI | ChessCoach AI |
|---|---|---|
| Knows your game history | ❌ | ✅ |
| Pattern detection across 500+ games | ❌ | ✅ |
| Personalized study plan | ❌ | ✅ |
| Works without uploading files manually | ❌ | ✅ |

---

## Environment Variables

Create a `.env` file based on `.env.example`:

| Variable | Description |
|---|---|
| `CHESSCOM_USERNAME` | Your Chess.com username |
| `GROQ_API_KEY` | Free API key from console.groq.com |

---

## License

MIT — feel free to fork and build on this.

---

*Built as a learning project to go deep on RAG pipelines, vector databases, and LLM integration using real personal data.*