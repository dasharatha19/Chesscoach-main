# ChessCoach AI — Legacy-Codebase Maturity Roadmap

This is the full plan discussed across our sessions, consolidated. Layers
build on each other in order — don't skip ahead, each depends on the one
before it being solid. Status is honest: ✅ done & verified, 🟡 started,
⬜ not started.

---

## Layer 1 — Tests (foundation for everything else)

- ✅ `tests/test_parse_pgn.py` — 14 tests covering header validation
  (`RawGameHeaders`, `validate_game_headers`) and the skip-and-continue
  behavior in `parse_pgn_file`. Verified passing against real code.
- ⬜ Tests for `chunker.py` (phase-splitting logic, empty-chunk skipping)
- ⬜ Tests for `router.py` (`classify_question` routing logic — harder,
  needs a mocked/fake Groq response rather than a real API call)
- ⬜ Tests for `embedder.py` (collection naming, idempotent create logic)
- ⬜ Tests for `app.py` endpoints (`/check`, `/setup`, `/ask` — using
  FastAPI's `TestClient`, with Qdrant/Groq mocked out, not real calls)

## Layer 2 — CI (automated checks on every push)

- ✅ `.github/workflows/ci.yml` — lints + runs backend tests on push/PR
  to `main`/`staging`; separately lints + builds the frontend.
  **Confirmed running on GitHub, passing.**
- ✅ `.github/workflows/keep-alive.yml` — created, confirmed registered
  and running on GitHub's schedule — but see Layer 5: GitHub's cron
  proved unreliable for this specific job, being replaced by
  UptimeRobot as the real mechanism. File left in repo, harmless.
- ⬜ Add `mypy` (type checking) once you're comfortable — optional,
  valuable given the Pydantic models we've added.

## Layer 3 — CD (deployment) — NOT STARTED

- ⬜ Backend → **Render**: connect your GitHub repo, one service for
  `main` (prod), a **second separate Render service** for `staging`
  (pre-prod) — different env vars, different Qdrant collections/keys
  if possible, so testing never touches real data.
- ⬜ Frontend → **Vercel**: connect the `frontend/` folder specifically
  (Vercel supports monorepo subfolder deploys) — same `main`/`staging`
  branch split, `NEXT_PUBLIC_API_URL` pointed at the matching backend.
- ⬜ Confirm the promotion flow works: feature branch → PR into
  `staging` → CI passes → merges → auto-deploys to pre-prod → you
  manually verify → PR `staging` → `main` → auto-deploys to prod.

## Layer 4 — Legacy-codebase maintenance hygiene

- ✅ `TODO.md` — tracks deferred, known issues with reasoning (not just
  a task list — includes *why* each is deferred and *when* to revisit).
- ⬜ `CHANGELOG.md` — dated, human-readable log of what shipped when.
  Different from git history — this is for a human skimming "what
  changed", not developers mid-work.
- ⬜ `.github/pull_request_template.md` — forces stating *why* a change
  was made, not just *what* — directly useful given how much of this
  project's "why" has lived only in chat so far.
- ⬜ **Dependabot** (`.github/dependabot.yml`) — free, built into GitHub,
  opens automatic PRs when a dependency has a security fix. Cheap to
  turn on.
- ⬜ Swap `print()` statements (throughout `fetch_games.py`, `embedder.py`,
  `parse_pgn.py`, etc.) for Python's `logging` module with levels — hard
  to search/filter raw prints once this is actually deployed on Render.
- ⬜ Basic error monitoring (e.g. free-tier Sentry) — right now, if `/ask`
  throws in production, you only find out if a user tells you.
- ⬜ `.env.example` — a committed template (no real secrets) listing
  every env var the app needs (`GROQ_API_KEY`, `QDRANT_URL`,
  `QDRANT_API_KEY`, `GROQ_MODEL`, `CHESSCOM_USERNAME`, `NEXT_PUBLIC_API_URL`)
  so setting up the project doesn't require reverse-engineering it from
  the source code.
- ⬜ Keep `CODEBASE_GUIDE.md` in sync — it currently describes the
  **older, single-user** version of this project (no query routing/
  rewriting, no multi-user collections) — worth a pass to update it to
  match what's actually in `src/` now, since a stale architecture doc
  is worse than no doc.

## Layer 5 — Already-known bugs (found through this conversation)

- ✅ `evaluate_rag.py` — missing `username` arguments on 3 calls (fixed,
  signature-verified).
- ✅ Deprecated Groq model `llama-3.3-70b-versatile` → `openai/gpt-oss-120b`,
  centralized into one `GROQ_MODEL` constant, env-var overridable
  (fixed, confirmed working against your real deployment).
- ✅ `ask_groq()` answer truncation — strengthened the length instruction
  + raised `max_tokens` as a safety margin (fixed, not yet re-confirmed
  by you against a fresh real answer).
- 🟡 `parse_pgn.py` — `played_as` silently defaults to `"black"` if
  username matches neither player. **Deliberately deferred** — see
  `TODO.md` for full reasoning. Must fix before the PGN-upload feature
  ships.
- ⬜ `app.py` — unused `BackgroundTasks` import/param (dead code, uses
  raw `threading.Thread` instead) — harmless but confusing, worth a
  clean single-purpose commit.
- ✅ `app.py` — unreachable code block in `setup_status()` (leftover
  from an older synchronous setup flow, left behind after the
  background-thread refactor) — removed, along with the now-unused
  `SetupResponse` model. Confirmed via tests + direct endpoint check
  that `/setup-status` behavior is unaffected.
- ⬜ `router.py`'s `rewrite_query()` — observed returning an **empty
  string** on a real question during testing (`Query rewritten:
  '...' → ''`). Pipeline didn't crash (fell through to unrewritten
  vector search), but worth investigating why the rewrite came back
  blank — noticed, not yet root-caused.
- ✅ `.gitignore` — `qdrant_storage/` (stale local Qdrant data, unused
  by current cloud-based code) added, preventing accidental commit of
  ~7MB of binary vector data.
- ✅ `retriever.py`'s `get_clients()` was rebuilding the embedding model
  from scratch on EVERY `/ask` call — originally fixed via module-level
  caching. **Now moot** — the HF Inference API migration removed the
  local embedding model from `get_clients()` entirely, so there's
  nothing left to cache or reload in the first place.
- ✅ `ruff` lint findings on `retriever.py` (import ordering, one
  `RUF015` generator-slicing fix) — cleaned, `ruff check` passes clean
  on this file now. Other files not yet linted by you.
- 🟡 **Render free-tier spin-down** — root cause found: GitHub Actions'
  `schedule` trigger unreliable for tight intervals, confirmed from
  Actions run-history timestamps. Switched to **UptimeRobot** (5-min
  interval). **Looks fixed** — a multi-hour stretch of clean
  `HEAD / 200 OK` pings with zero `"Shutting down"` lines observed —
  but not yet confirmed over a full day/week of continuous uptime.
  `keep-alive.yml` left in the repo, no longer the actual mechanism.
- ✅ **Render OOM crash** (`"Ran out of memory (used over 512MB)"`,
  confirmed directly from Render's own error message) — root cause:
  the local embedding model (fastembed/ONNX) being loaded into the
  container's memory, sometimes twice (see the old Layer 6 entry this
  replaces). **Fixed by removing local model loading entirely** —
  migrated to Hugging Face's Inference API (new `src/embeddings.py`,
  shared by `embedder.py` and `retriever.py`). `fastembed` (and its
  heavy `onnxruntime` dependency) removed from `pyproject.toml`
  entirely. Confirmed locally: a real HF API call returns a correct
  384-dim vector (matches Qdrant's expected vector size exactly).
  **Not yet confirmed on Render** — needs a real `/setup` run against
  deployed pre-prod, watching memory, before calling this fully closed.

## Layer 6 — Things noticed but not yet decided on

- The `retrieve_relevant_chunks(limit=8)` / aggregate-stats split
  doesn't yet scale gracefully to power users with thousands of games
  (discussed at length — tiered/hierarchical retrieval is the real
  answer, not yet designed or built).
- `get_aggregate_stats()` doesn't surface rating (`my_rating`) data to
  the LLM at all, even though it's in the CSV — found while validating
  a real answer about "what's my actual Elo." Not yet fixed, agreed as
  a legitimate small enhancement whenever you want it.
- Multi-modal input (PGN upload, Lichess import, screenshot/vision,
  Stockfish enrichment) — all discussed as future work, none started.
  PGN upload is the cheapest next step; Stockfish enrichment is the
  highest-value one for actual coaching quality.
- **`embedder.py` and `retriever.py` each independently create their
  own `TextEmbedding` instance** — ~~Noticed, not yet fixed~~
  **Superseded — see Layer 5's "Render OOM crash" entry.** Rather than
  sharing one local model instance between the two files, both local
  loading paths were removed entirely in favor of HF's Inference API.
  This didn't just fix the duplication, it eliminated local model
  memory usage altogether.

## Layer 7 — Planned: RAG quality evaluation (RAGAS / DeepEval)

**Explicitly queued for AFTER the Render spin-down issue is confirmed
fixed — not started now.**

- ⬜ Add **RAGAS** — reference-free RAG metrics: faithfulness (is the
  answer actually supported by retrieved context?), answer relevancy,
  context precision, context recall. Can auto-generate a synthetic
  eval dataset from your own data, so no hand-labeling needed to
  start. Recommended entry point — replaces/extends the hand-rolled
  LLM-as-judge approach already in `evaluate_rag.py`.
- ⬜ Add **DeepEval** — same metric family, but `pytest`-native, so it
  plugs directly into the CI workflow already working (`ci.yml`) as an
  actual regression gate: RAG answer quality becomes something that
  can fail a build, not something only checked by eyeballing answers
  manually.
- ⬜ Decide: keep the existing hand-rolled `evaluate_rag.py` alongside
  these, or retire it once RAGAS covers the same ground with less
  custom code to maintain.

---

**Suggested order from here, staying one-thing-at-a-time:**
1. **Run a full local `/setup` (real batched chunks, not just one test sentence), then push the HF embeddings migration to `staging`, redeploy pre-prod, and confirm the OOM crash is actually gone under real load.** Current top priority.
2. Fix the remaining `app.py` Layer-5 item (unused `BackgroundTasks` param) — small, isolated.
3. Investigate the empty query-rewrite issue.
4. Confirm UptimeRobot's fix holds over a longer stretch (a day+) before fully trusting it.
5. Then move to Layer 3 (Render + Vercel CD setup — staging/prod split).
6. Layer 4 hygiene items can be picked off individually, anytime, since none of them depend on each other.
7. **Layer 7 (RAGAS/DeepEval)** — once everything above is stable, not before. (DeepEval was the agreed pick — pytest-native, plugs into the existing `ci.yml`.)