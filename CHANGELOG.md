# Changelog

All notable changes to ChessCoach AI are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/) —
newest entries at the top, grouped by release, each release grouped
by Added / Changed / Fixed / Removed.

## [Unreleased] — currently on `staging`, not yet released to `main`

### Added
- Header validation layer in `parse_pgn.py` (`RawGameHeaders`,
  `validate_game_headers`) — bad/malformed Chess.com data is now
  rejected with a specific logged reason instead of silently
  defaulting.
- `tests/test_parse_pgn.py` — 14 automated tests covering the above.
- `.github/workflows/ci.yml` — lint + test on every push/PR.
- `.github/workflows/keep-alive.yml` — later found unreliable for
  this purpose, superseded by UptimeRobot (external ping service).
- `/health`, `/ready`, `/health/db` endpoints — liveness, readiness,
  and dependency-specific health checks.
- `check_qdrant.py` — inspect real Qdrant collection contents.
- `TODO.md` / `ROADMAP.md` — ongoing project tracking docs.

### Changed
- Centralized the Groq model name into one `GROQ_MODEL` constant
  (env-var overridable) instead of 4 separate hardcoded strings.
- `retriever.py`'s `get_clients()` now caches the embedding model at
  module level instead of reloading it on every single `/ask` request.
- Strengthened the answer length instruction in `ask_groq()`'s prompt
  + raised `max_tokens` as a safety margin, to stop mid-sentence
  truncation.
- App version is now read via `importlib.metadata` at startup (single
  source of truth, taken from the installed package) instead of being
  hardcoded separately in 2 places.
- `/` now supports `HEAD` requests, not just `GET` (uptime monitors
  ping with HEAD by default).

### Fixed
- App startup crashed on Render (`FileNotFoundError: pyproject.toml`)
  — the version lookup assumed the raw source file would be present
  at runtime, which isn't guaranteed inside a deployed container.
  Switched to `importlib.metadata` (reads the installed package's own
  version, not a raw file path) — confirmed working even with zero
  access to `pyproject.toml` at runtime.
- `evaluate_rag.py` — calls to `get_aggregate_stats()`,
  `retrieve_relevant_chunks()`, and `ask_groq()` were missing the
  required `username` argument after the multi-user refactor.
- Deprecated Groq model `llama-3.3-70b-versatile` (decommissioned by
  Groq 2026-08-16) replaced with `openai/gpt-oss-120b`.
- `qdrant_storage/` (stale local Qdrant data) added to `.gitignore` —
  was at risk of being committed.

---

## How releases work from here

When `staging` is merged into `main` for an actual release:
1. Move everything out of `[Unreleased]` into a new dated section,
   e.g. `## [1.0.0] - 2026-10-15`
2. Leave a fresh, empty `[Unreleased]` section at the top for whatever
   comes next.
3. Tag the merge commit in git: `git tag v1.0.0 && git push --tags`
   — this is what actually lets you revert to this exact code state
   later (`git checkout v1.0.0`), not just read about it here. The
   CHANGELOG is the human-readable story; the git tag is the
   technical anchor pointing at the exact commit.