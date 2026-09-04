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
- ⬜ `app.py` — unreachable code block in `setup_username()` (a full
  `SetupResponse`-returning block sitting after an earlier `return`
  in the same function) — needs a decision: which version was the
  actual intent?
- ⬜ `router.py`'s `rewrite_query()` — observed returning an **empty
  string** on a real question during testing (`Query rewritten:
  '...' → ''`). Pipeline didn't crash (fell through to unrewritten
  vector search), but worth investigating why the rewrite came back
  blank — noticed, not yet root-caused.
- ✅ `.gitignore` — `qdrant_storage/` (stale local Qdrant data, unused
  by current cloud-based code) added, preventing accidental commit of
  ~7MB of binary vector data.
- ✅ `retriever.py`'s `get_clients()` was rebuilding the embedding model
  from scratch on EVERY `/ask` call — now cached at module level after
  first load, reused for all later calls. Likely contributor to Render
  memory pressure (fixed, not yet re-confirmed under real load).
- ✅ `ruff` lint findings on `retriever.py` (import ordering, one
  `RUF015` generator-slicing fix) — cleaned, `ruff check` passes clean
  on this file now. Other files not yet linted by you.
- 🟡 **Render free-tier spin-down** — confirmed via Render logs the
  service was sleeping after ~15 min idle, then sitting dark for
  1.5–5 hours before the next wake. Root cause found: GitHub Actions'
  `schedule` trigger is documented as unreliable for tight intervals
  (`*/10 * * * *` only fired ~6 times over 24h instead of ~144 expected
  — confirmed directly from the Actions run history timestamps).
  **Fix in progress: switching to UptimeRobot** (external, purpose-built
  ping service, 5-min interval) instead of relying on GitHub's cron.
  `keep-alive.yml` left in the repo but no longer the actual mechanism.
  **Not yet confirmed fixed** — need to watch Render logs post-UptimeRobot
  setup for a `"Shutting down"`-free stretch.

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
  own `TextEmbedding` instance** — during a real `/setup` run, the log
  showed "Fetching 5 files" (the HuggingFace model download) happen
  **twice** in one deploy: once in `embedder.py` during game embedding,
  once again in `retriever.py`'s `get_clients()` on the first `/ask`.
  The `get_clients()` caching fix (Layer 5) only prevents *repeat*
  loads within `retriever.py` itself — it doesn't share a model
  instance with `embedder.py`'s separate copy. Net effect: up to two
  full embedding-model instances resident in memory at once, on a
  memory-constrained free-tier container. Noticed, not yet fixed —
  real fix would be a single shared embedding-model singleton used by
  both files, not two independent ones.

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
1. **Set up UptimeRobot, confirm Render stops showing "Shutting down" in its logs.** Current top priority — everything else waits on a stable, always-on backend to test against.
2. Investigate the double embedding-model-load issue (Layer 6) — likely helps the memory/stability picture further.
3. Fix the two remaining `app.py` Layer-5 items (dead code + unreachable block) — small, isolated.
4. Investigate the empty query-rewrite issue.
5. Then move to Layer 3 (Render + Vercel CD setup — staging/prod split).
6. Layer 4 hygiene items can be picked off individually, anytime, since none of them depend on each other.
7. **Layer 7 (RAGAS/DeepEval)** — once everything above is stable, not before.