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
- 🔺 **ELEVATED PRIORITY** (was a routine hygiene item, now justified by
  direct experience): swap `print()` statements for Python's `logging`
  module with real levels (`DEBUG`/`INFO`/`WARNING`/`ERROR`) throughout
  `fetch_games.py`, `embedder.py`, `parse_pgn.py`, `router.py`,
  `retriever.py`. **Why this jumped priority:** the entire OOM crash,
  model deprecation, `401`, and reasoning-token investigations this
  session were all diagnosed by manually scrolling unstructured Render
  logs where a real error looks identical to a routine health-check
  ping. A real `logging` setup would let Render's log view be filtered
  by severity — "show me only real problems" — instead of scrolling
  hundreds of `HEAD / 200 OK` lines to find the one that matters.
- ⬜ Basic error monitoring (e.g. free-tier Sentry) — right now, if `/ask`
  throws in production, you only find out if a user tells you.
- ⬜ `.env.example` — a committed template (no real secrets) listing
  every env var the app needs (`GROQ_API_KEY`, `QDRANT_URL`,
  `QDRANT_API_KEY`, `GROQ_MODEL`, `HF_TOKEN`, `CHESSCOM_USERNAME`,
  `NEXT_PUBLIC_API_URL`) so setting up the project doesn't require
  reverse-engineering it from the source code.
- ⬜ Keep `CODEBASE_GUIDE.md` in sync — it currently describes the
  **older, single-user** version of this project (no query routing/
  rewriting, no multi-user collections, no HF embeddings) — worth a
  pass to update it to match what's actually in `src/` now.

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
  '...' → ''`). ~~Pipeline didn't crash... not yet root-caused.~~
  **ROOT-CAUSED AND FIXED:** `openai/gpt-oss-120b` is a *reasoning*
  model — it spends completion tokens on internal chain-of-thought
  BEFORE writing visible content. `max_tokens=30` was too small a
  budget; reasoning was consuming it entirely, leaving nothing for
  actual output. **Confirmed directly** via Groq's own
  `reasoning_tokens` usage field: a real test showed 60 reasoning
  tokens consumed against the old 30-token budget — structurally
  impossible to have worked. Fix: raised `max_tokens` to 150, added
  `reasoning_effort="low"`, added a defensive fallback to the original
  question if still empty, switched to `openai/gpt-oss-20b` (separate
  quota from the main answer-generation model, faster). **Confirmed
  working** on a real deployed test — `finish_reason=stop`, real
  rewritten query produced.
- ⬜ `router.py`'s `classify_question()` — **same suspected root cause**
  as above (even tighter old budget, `max_tokens=10`), circumstantial
  evidence was every question routing to `hybrid` regardless of
  content. **Confirmed via diagnostics**: old budget (10) was smaller
  than a single real test's `reasoning_tokens=33` — same structural
  impossibility. Same fix applied (raised to `max_tokens=50`,
  `reasoning_effort="low"`, `gpt-oss-20b`, explicit `valid_routes`
  fallback defaulting to `"hybrid"` on any unexpected output).
  **Confirmed working** on a real test — correctly classified an
  example-seeking question as `specific`, not reflexively `hybrid`.
- 🟡 **New, separate issue found while verifying the above:**
  `rewrite_query()`'s prompt instructs the model to inject a game
  phase and a piece color into every rewrite (even when the user's
  original question specified neither) — observed turning "show me a
  game where I lost quickly" into "quick loss **opening white**,"
  inventing specifics the user never stated. This could actively
  *narrow* vector search away from the correct chunk (e.g. if the
  real fastest loss was as Black, or a middlegame blunder). **Not
  fixed reactively** — deliberately deferred to be measured properly
  once DeepEval (Layer 7) is running, using `context_precision` to
  compare rewrite-on vs. rewrite-off / prompt-adjusted vs. not, with
  real data instead of judging from one example.
- 🟡 **Diagnostic logging added to `rewrite_query`/`classify_question`**
  (`reasoning_tokens`, `finish_reason`, `completion_tokens` per call)
  — deliberately temporary/testing-phase. Once fully trusted (no more
  `finish_reason=length` ever observed), downgrade these from plain
  `print()` to `logger.debug()` rather than deleting them outright —
  see the elevated logging item below.
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
- 🟡 **Render OOM crash** (`"Ran out of memory (used over 512MB)"`,
  confirmed directly from Render's own error message) — root cause:
  the local embedding model (fastembed/ONNX) being loaded into the
  container's memory. **Fix attempted:** migrated to Hugging Face's
  Inference API (`src/embeddings.py`), `fastembed`/`onnxruntime`
  removed from `pyproject.toml`. Confirmed locally: a real HF API call
  returns a correct 384-dim vector. **Deployed fix did NOT resolve it
  on first redeploy** — `onnxruntime` warning still appeared in
  post-deploy logs, meaning the OLD code/dependencies were still what
  actually ran. Leading suspect: **`uv.lock` was never regenerated**
  after editing `pyproject.toml`, so `uv sync` on Render installed the
  stale locked dependency set (still including `fastembed`) rather
  than the updated one. Needs: `uv lock` run locally, the regenerated
  lockfile committed and pushed, then re-verified on a fresh deploy.

## Layer 6 — Things noticed but not yet decided on

- `get_aggregate_stats()` doesn't surface rating (`my_rating`) data to
  the LLM at all, even though it's in the CSV — found while validating
  a real answer about "what's my actual Elo." Not yet fixed, agreed as
  a legitimate small enhancement whenever you want it.
- Multi-modal input (PGN upload, Lichess import, screenshot/vision,
  Stockfish enrichment) — see Layer 8 below, now fully broken out with
  priority ordering.
- **`embedder.py` and `retriever.py` each independently create their
  own `TextEmbedding` instance** — ~~Noticed, not yet fixed~~
  **Superseded — see Layer 5's "Render OOM crash" entry.** Rather than
  sharing one local model instance between the two files, both local
  loading paths were removed entirely in favor of HF's Inference API.

### Tiered retrieval (decision made — doubts.txt 1.4)

**Decision:** don't store or embed a user's entire game history as
data grows (the "10k games" worry). Use three tiers:

1. **Aggregate stats** — computed with pandas over the user's **full**
   history regardless of size. This already scales fine (10k rows is
   nothing for pandas) and is what answers "what's my win rate."
2. **Vector search** — bounded to a **recent window** (e.g. last
   500 games or last 6–12 months, whichever is smaller), embedded into
   Qdrant. This is what answers "show me examples of X" and keeps
   collection size — and therefore search latency — bounded no matter
   how long someone's been playing.
3. **Cold storage** (optional, later) — older games kept but never
   embedded. Only pulled into the vector tier on demand if a query
   explicitly references an older time period ("compare my openings
   from last year to now").

This directly resolves the "do we store 10k games in the vector DB"
question — no, tier 1 always sees everything, tier 2 never grows
unbounded.

**⚠️ Open gap found while reviewing this (not yet solved):** Tier 1
currently depends on `get_aggregate_stats()` reading a **local CSV
file** on disk (`data/processed/`). Local container disk on Render is
**not reliably persistent** across redeploys/restarts — so the "full
history, always available" promise of Tier 1 doesn't actually hold
today unless that CSV survives, which it currently isn't guaranteed
to. **This means Qdrant alone is not a sufficient datastore for this
architecture** — a separate persistent store for the exact/structured
game data is needed alongside it, not instead of it. Real options,
cheapest to most robust:
- Re-derive the CSV from Chess.com on every `/setup` (no persistence
  needed, but stats are only as fresh as the last sync)
- **A real lightweight database (e.g. Postgres — Render has a free
  tier) for the structured per-game data**, queried directly instead
  of via a CSV file — this is the architecturally correct fix
- Store full row data in Qdrant payloads too (avoids a second
  database, but conflates two different jobs into one store)

Not designed or built yet — needs a decision before Tier 1 can be
trusted in production at any real scale.

**Update — leaning decision, not yet built:** discussed using
**Supabase** (hosted Postgres + a real web dashboard) instead of
either a plain CSV file or a self-managed Postgres instance — solves
the persistence gap AND the "how do I actually look at this data"
problem in one move, since self-hosted Postgres alone would still need
a separate tool just to browse tables. Bundled with a second,
related, deliberately-deferred decision: whether to remove/raise the
current 6-month game history cap (`fetch_games.py`) once there's a
real persistent store capable of holding full account history instead
of just a recent window. Both explicitly parked for later — not
started.

**Decision confirmed, migration in progress:**
- ✅ Moving forward with Supabase (Postgres). Confirmed: free tier
  allows 2 active projects, well-suited to a staging/prod split.
- 🟡 **Constraint found:** account already has 1 of 2 free Supabase
  project slots used by an unrelated project — only 1 slot available
  for ChessCoach. **Resolution (pending confirmation):** use ONE
  Supabase project with two Postgres **schemas** (`prod`, `staging`)
  rather than two separate projects — genuinely isolated (a query
  against `prod.games` cannot touch `staging.games`), and arguably the
  more correct Postgres-native solution regardless of slot
  availability, not just a workaround.
- ✅ **RLS (Row Level Security) — decided OFF / not applicable.**
  Reasoning: the backend connects via a direct Postgres connection
  string using the `postgres` role, which bypasses RLS regardless of
  its setting — RLS only matters if the frontend ever queries Supabase
  directly via their client SDK, which this architecture doesn't do.
  Revisit only if that changes.
- ✅ `src/db.py` created — shared Postgres connection module
  (`get_db_connection()`, `check_db_connection()`), same pattern as
  `embeddings.py` for HF. `psycopg2-binary` added as a dependency.
  **Not yet tested against a live Supabase instance.**
- 🟡 `/ready` extended with a Supabase connectivity check; new
  `/health/supabase` endpoint added (mirrors the existing
  `/health/db` Qdrant-latency pattern). **Written but unverified** —
  no live Supabase project connected yet to test against.
- ⬜ Still needed before this is usable: the actual `games` table
  schema (blocked on getting real CSV column names / `extract_game_data()`
  from the user), migrating `get_aggregate_stats()` and the `/setup`
  pipeline to read/write Postgres instead of the local CSV, and
  extending UptimeRobot's ping target (or `/ready`) to prevent the
  free Supabase project's 7-day inactivity auto-pause.

## Layer 7 — Planned: RAG quality evaluation (RAGAS / DeepEval)

**Explicitly queued for AFTER the Render OOM/spin-down issues are
confirmed fixed — not started now.**

- ⬜ Add **RAGAS** — reference-free RAG metrics: faithfulness (is the
  answer actually supported by retrieved context?), answer relevancy,
  context precision, context recall. Can auto-generate a synthetic
  eval dataset from your own data, so no hand-labeling needed to
  start.
- ⬜ Add **DeepEval** (agreed pick) — same metric family, but
  `pytest`-native, so it plugs directly into the already-working
  `ci.yml` as an actual regression gate.
- ⬜ Decide: keep the existing hand-rolled `evaluate_rag.py` alongside
  these, or retire it once DeepEval covers the same ground.

## Layer 8 — Multi-modal / alternate data ingestion (NOT STARTED)

Priority order, cheapest-and-safest first — do NOT try to solve all
of these at once:

- ⬜ **PGN upload** (cheapest, do first). Reuses `parse_pgn.py`
  directly. **Hard-blocked on TODO.md item #1 (`played_as` defaulting
  bug)** — an uploaded PGN is untrusted input where the username might
  not appear in the game at all, exactly the case that bug breaks on.
  Fix the bug first, then wire the upload endpoint.
- ⬜ **Lichess import.** Different API, same shape of problem as
  Chess.com — needs its own fetch → validate → adapt step, outputting
  the *same internal schema* so downstream code doesn't need to know
  the source.
- ⬜ **Screenshot / board-image input.** Needs a vision model or
  chess-specific board-recognition. A misread square silently produces
  a wrong position → confidently wrong coaching advice. Don't start
  before PGN upload and Lichess import are solid.
- ⬜ **Video / livestream links.** Out of scope for now — research-grade
  problem, not a weekend feature.
- ⬜ **Text/book input** (chess theory PDFs). Different problem entirely
  — generic RAG-over-documents, not game-data parsing. Treat as a
  separate mini-project.

**Decision (doubts.txt 2.1):** use `python-chess`'s real PGN parser
for all of these, never regex — already your own conclusion, confirmed
correct.

## Layer 9 — Response caching (decision made, not yet built)

- ⬜ Cache `/ask` responses keyed on
  `(username, route, normalized_question, data_version)`.
  `data_version` = bumped every time that user's data is re-synced —
  without it, a cached answer survives a data refresh and serves
  stale stats.
- ⬜ Start with a plain in-memory dict + TTL — **not Redis yet.** Redis
  only earns its keep once there are multiple server instances (Layer
  3's CD plan doesn't include horizontal scaling yet).
- ⬜ Only cache the `aggregate`/`specific` routes' final answers — don't
  cache retrieval separately from generation.

## Layer 10 — Chess.com API resilience (decision made, partially in place)

Header validation (`RawGameHeaders`/`validate_game_headers`, already
shipped) **is** most of an adapter pattern — fetch → validate →
transform is already structurally separated. Still missing:

- ⬜ **Contract test** — a scheduled job (external scheduler, given
  Layer 5's finding that GitHub's cron is unreliable) that fetches one
  known-stable public game and asserts the field shape still matches
  expectations — catches a Chess.com schema change within minutes
  instead of via a user-reported broken `/setup`.
- ⬜ Route the existing >20%-batch-failure warning to real monitoring
  (Sentry, Layer 4) instead of console-only.

**Decision (doubts.txt 1.1):** don't build a heavier abstraction than
this — validate-then-transform, repeated per-source, is enough for one
data source plus one planned second source (Lichess).

## Layer 11 — Scaling & concurrency (validated against external review)

An independent review of the architecture reached the same conclusions
already reflected here — good convergence signal, not new direction.

- ✅ **Decision confirmed:** no Triton, custom batching, Kubernetes, or
  self-hosted GPU inference needed. Groq owns LLM-side scaling; the
  job here is only making FastAPI handle concurrent requests well,
  which it already does by default (`def` routes run in a threadpool).
- ✅ **Decision confirmed:** keep `WEB_CONCURRENCY=1` on Render until
  real load testing shows it's actually the bottleneck. Don't
  pre-emptively raise it — more workers costs more RAM, which directly
  conflicts with the still-unresolved OOM situation (Layer 5).
- ⬜ **Add timing logs to `/ask`** — log `embedding_time`, `qdrant_time`,
  `groq_time`, `total_time` per request. This is the actual next
  action, before any load testing: turns "something feels slow" into
  a measurement instead of a guess.
- ⬜ **Staged concurrency test** — 1 user → 5 simultaneous → 10
  simultaneous, record each user's total latency.
  - Flat latency across users → fine as-is, no action needed.
  - Latency climbing with each added user → something is serializing;
    the timing logs above pinpoint which stage.
- ⬜ **Qdrant environment isolation — decision point, not yet made:**
  either (a) a second, fully separate Qdrant cluster for `staging`
  (cleaner isolation, costs more), or (b) one shared cluster with
  environment-prefixed collection names (`prod_<user>` vs
  `staging_<user>`) — cheaper, still isolates data, but depends on the
  backend always deriving the correct prefix correctly. Pick one
  before pre-prod testing risks touching real user data.
- **General principle to reuse for any future scaling worry:** don't
  add infrastructure for a bottleneck that hasn't been measured yet.
  Add observability → generate real load → read the actual numbers →
  fix the specific thing the numbers point at.

## Layer 12 — Agentic tool-calling (design agreed, not started — depends on Layer 6's Supabase work landing first)

**Correctly identified:** the current app is a fixed RAG *pipeline*
(hardcoded classify → rewrite → retrieve → generate), not an *agent*
— the LLM never decides for itself that it needs more data than
what's already loaded; every step is predetermined in Python.

- ✅ **Feasibility confirmed:** `gpt-oss-120b`/`gpt-oss-20b` on Groq
  genuinely support real function/tool calling ("local tool calling"
  — custom functions you define, as opposed to Groq's server-side
  built-in tools like `browser_search`), explicitly marketed for
  agentic use.
- ✅ **Design decision — two separate problems, not one:**
  1. *"Does the data exist in storage yet?"* — a storage/sync
     problem, solved by Supabase becoming an incrementally-growing
     persistent store (Layer 6), independent of any single
     conversation.
  2. *"Does the LLM know when it needs more than what's loaded?"* —
     the actual agentic piece: a tool like
     `query_extended_history(username, date_range)` that queries
     **already-stored** Supabase data (fast SQL, no blocking live
     call). If data isn't synced yet, the tool reports that and
     *separately* triggers a background resync (same fire-and-poll
     pattern as the existing `/setup` flow) — never a live,
     synchronous Chess.com fetch inside a chat response.
- **Why not a literal "agent calls Chess.com live" design:**
  Chess.com's API only supports reliable *serial* requests (see
  Layer 10) — fetching a very active player's full history live,
  inside one chat turn, could take tens of seconds to minutes. Bad UX,
  avoidable by separating sync from query as above.
- ⬜ Not started. Explicitly sequenced AFTER Supabase (Layer 6) is
  fully working — no sensible "extended history" tool to build while
  the underlying storage is still an ephemeral CSV.

### Related future feature — "compare me to a star player" (noted, not started)

Different from the above — this is **public, shared reference data**
(famous players' games), not a user's own private history. Should NOT
live in the per-user-isolated pattern (not per-user Qdrant
collections, not per-user Postgres rows) — needs its own separate,
shared table (e.g. `reference_games`, no `username` column) queryable
by every user. Distinct feature, not part of the current Supabase
migration.

---

**Suggested order from here, staying one-thing-at-a-time:**
1. **Supabase migration (Layer 6)** — currently in progress. Confirm
   the 1-slot/schema-split plan, get the real CSV schema, build
   `games` table(s), migrate `get_aggregate_stats()` + `/setup`, test
   `/ready` and `/health/supabase` against the real instance, extend
   UptimeRobot/`/ready` to prevent the 7-day auto-pause.
3. Add timing logs to `/ask` (Layer 11) — cheap, and needed before any
   concurrency testing means anything.
4. Fix the remaining `app.py` Layer-5 item (unused `BackgroundTasks`
   param) — small, isolated.
5. Investigate the empty query-rewrite issue.
6. Confirm UptimeRobot's fix holds over a longer stretch before fully
   trusting it.
7. Pick the Qdrant staging-isolation approach (Layer 11) before doing
   heavier pre-prod testing.
8. Then move to Layer 3 (Render + Vercel CD setup — staging/prod split).
9. Run the staged concurrency test (Layer 11) once the above is stable.
10. Layer 4 hygiene items — anytime, independent of each other.
11. **Layer 7 (DeepEval)** — once everything above is stable, not before.