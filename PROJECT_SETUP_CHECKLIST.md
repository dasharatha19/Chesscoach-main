# GitHub Repository Setup & Security Checklist
<!-- Reuse this file for every new repository, fork, and production project. -->
<!-- Last reviewed: 2026-10-09 -->

A practical, reusable checklist for creating and maintaining secure, maintainable repositories, especially Python, AI/ML, computer-vision, LLM/RAG, API, Docker, and MLOps projects.

> **How to use this file**
> 1. Keep the master copy in a private notes repository or your `ai-ml-project-template`.
> 2. Copy it into each new repository as `PROJECT_SETUP_CHECKLIST.md`.
> 3. Tick items as you complete them. Mark irrelevant items `N/A`.
> 4. GitHub settings are not all copied by a template or fork. Verify them in each repository.
> 5. Treat this as a baseline, not a guarantee of security. Adapt it to your threat model, project, account plan, and deployment environment.

---

## A. Agent execution protocol (read this first if you are an AI coding agent)

This file is both a human checklist and a work order for an AI coding agent (Claude Code, Codex, Copilot agent, etc.). Follow these rules:

**Status markers**

| Marker | Meaning |
|---|---|
| `[ ]` | Not done |
| `[~]` | In progress or partially done (add a one-line note) |
| `[x]` | Done **and verified** (add evidence: file path, PR link, or command output summary) |
| `[N/A]` | Not applicable (add the reason) |
| `[H]` | Needs the human (GitHub UI setting, cloud console, account-level change, or a secret). Do not fake it |

**Rules**

1. Work top to bottom, but do the **repo-file items first** (README, `.gitignore`, `.env.example`, `dependabot.yml`, CI workflow, `SECURITY.md`, `CODEOWNERS`, templates, Dockerfile hardening, tests). These are 🤖 agent-doable.
2. Items under **Section 3 (GitHub Code security settings)**, **Section 7 (branch protection / rulesets)**, and **Section 15 (settings audit)** live in GitHub settings. Mark them `[H]` unless you have an authenticated `gh` CLI with admin rights, and even then, **tell the human what you changed**.
3. **Never** ask for, print, commit, or log a secret. If a real secret is found in the repo or history, stop, report it, and mark the rotation item `[H]`.
4. Make small, reviewable commits/PRs, one logical group per PR (for example "add dependabot + CI", then "harden Dockerfile"). Follow the repository's branching strategy (see Appendix A for ChessCoach: work lands on `staging`, never directly on `main`).
5. After each item, **verify** it (run the tests, lint, `docker build`, validate YAML) before ticking it. "I wrote the file" is not the same as "it works".
6. Do not enable "required status checks" until the check names exist and pass reliably.
7. Do not upgrade major dependency versions as part of this checklist unless an item explicitly requires it.
8. When finished with a pass, fill in **Appendix B (progress log)** with date, what changed, and what is left for the human.
9. If an item conflicts with what the project actually does, mark `[N/A]` with the reason instead of forcing it.

---

## 0. Before creating the repository

- [ ] Decide whether the repository should be **public** or **private**. Never make a repository public until secrets, data, licenses, and history have been reviewed.
- [ ] Choose a clear repository name and description.
- [ ] Decide whether to create from a **template** or **fork** an existing repository.
- [ ] Check the source project's license and attribution requirements.
- [ ] Identify the project's language, package manager, runtime, deployment target, and CI system.
- [ ] Decide where secrets will live (local environment variables, GitHub Actions secrets, or a cloud secret manager).
- [ ] Decide whether datasets, model weights, generated files, and artifacts belong in Git, Git LFS, or external object storage.
- [ ] Add an owner/maintainer and a short project goal.

## 1. Repository basics

- [ ] Add a useful `README.md` with purpose, features, prerequisites, installation, usage, testing, configuration, and deployment.
- [ ] Add a suitable `LICENSE` if the project will be distributed or open source.
- [ ] Add `.gitignore` for the language and tools (Python, Node, IDE files, environments, datasets, model weights, logs, caches, secrets).
- [ ] Add `CONTRIBUTING.md` if you expect external contributions.
- [ ] Add `CODE_OF_CONDUCT.md` for a community project, if appropriate.
- [ ] Add `SECURITY.md` with a private vulnerability-reporting route (see Section 1a).
- [ ] Add `.github/PULL_REQUEST_TEMPLATE.md` if PRs are part of your workflow.
- [ ] Add issue templates or GitHub issue forms if useful.
- [ ] Add `CODEOWNERS` for projects with multiple maintainers (for a solo repo it still helps auto-request your review and protects `.github/` and deployment files).
- [ ] Add `CHANGELOG.md` and keep it updated per release.
- [ ] Set repository topics and a useful description.
- [ ] Choose and document the default branch (`main` is a common choice) and the branching strategy.
- [ ] Review repository visibility, collaborators, outside collaborators, and app access.
- [ ] 👤 Enable **auto-delete head branches** after merge (Settings → General) if you use feature branches.

### 1a. `SECURITY.md` minimum content

- [ ] Supported versions (or "latest `main` only").
- [ ] How to report a vulnerability privately (a contact email, and/or enable GitHub **Private vulnerability reporting**: 👤 Settings → Code security).
- [ ] Expected response time (honest, for example "best effort within 7 days").
- [ ] What is in scope and out of scope.

## 2. Git hygiene and secrets

- [ ] Add `.env`, `.env.*` (with an explicit exception for a safe `.env.example`), private keys, credentials, local databases, and generated secrets to `.gitignore`.
- [ ] Commit `.env.example` containing **placeholder values only**, never working credentials. It should list **every** variable the app reads.
- [ ] Keep tokens, API keys, passwords, cloud credentials, private certificates, and production connection strings out of source code and Git history.
- [ ] Use environment variables locally and a secret manager, GitHub Actions secrets, or the hosting platform's env-var store in automation and deployment.
- [ ] Never print secrets into CI logs, notebook output, exception messages, or screenshots.
- [ ] Check that notebooks do not contain credentials or sensitive output before committing (consider `nbstripout`).
- [ ] Before publishing a previously private repository, review the complete Git history, issues, releases, artifacts, and Actions logs.
- [ ] If a real secret is exposed, revoke/rotate it immediately; removing it from the latest commit is not enough. See the incident runbook in Section 2a.
- [ ] Run **Gitleaks** (or an equivalent) locally and in CI, including a one-time scan of the full history (`gitleaks detect`).
- [ ] Add **pre-commit** hooks (see Section 5a) so secrets and formatting problems are caught before they reach GitHub.
- [ ] Use least-privilege tokens; prefer short-lived credentials or OIDC federation over long-lived cloud keys where supported.
- [ ] Use **different keys for dev, staging, and production** so a leak in one environment does not compromise the others.
- [ ] Give every third-party API key (LLM, embeddings, vector DB) a **spend/usage limit** in the provider dashboard where available.

### 2a. Secret-leak incident runbook (keep it short and actually follow it)

1. **Revoke/rotate** the key at the provider first. Speed matters more than cleanliness.
2. Update the new key in the deployment platform and GitHub Actions secrets.
3. Check provider usage logs for unexpected activity.
4. Remove the secret from the repo. Rewriting history (`git filter-repo` / BFG) is optional once the key is dead; the key must be treated as compromised either way.
5. Add a test or hook (Gitleaks) so the same class of leak is caught next time.
6. Note the incident in the changelog or private notes.

## 2b. Account-level security

- [ ] 👤 Two-factor authentication or **passkeys** enabled on the GitHub account (and on Render, Vercel, Qdrant, Groq, Hugging Face, and any other provider account).
- [ ] 👤 Prefer **fine-grained personal access tokens** with a short expiry over classic tokens; delete tokens you no longer use.
- [ ] 👤 Review authorized OAuth apps, GitHub Apps, SSH keys, and deploy keys periodically.
- [ ] 👤 Consider **signed commits** (SSH or GPG signing) and/or "Vigilant mode" if provenance matters.
- [ ] 👤 Store recovery codes somewhere safe and offline.

## 3. GitHub Code security settings (👤 usually human-only)

Open **Repository → Settings → Security and quality / Code security** (labels vary by GitHub UI and plan). Enable the options available and appropriate to the repository.

- [ ] **Dependency graph**: enable it to see detected dependencies.
- [ ] **Dependabot alerts**: enable notifications for known vulnerable dependencies.
- [ ] **Dependabot security updates**: enable automatic security-fix pull requests where available.
- [ ] **Dependabot version updates**: configure via `.github/dependabot.yml`; this is separate from security updates.
- [ ] **Secret scanning**: enable where available.
- [ ] **Push protection**: enable where available to block supported secrets before they are pushed.
- [ ] **Code scanning / CodeQL**: enable default setup for supported languages where available; otherwise consider a reviewed custom workflow or another scanner.
- [ ] **Private vulnerability reporting**: enable if you accept external reports.
- [ ] Review alert notification settings and make sure someone will actually see and triage alerts.
- [ ] Review the repository's available plan/feature entitlements; features vary by visibility, account plan, and product.
- [ ] Revisit security settings when transferring a repository, changing visibility, or creating a fork.

### Automatic dependency submission: how to decide

- [ ] Enable it only when useful and supported by your repository's ecosystem and configuration.
- [ ] Remember it requires the dependency graph and GitHub Actions.
- [ ] For ecosystems with Dependabot graph jobs (currently including Python and Go per GitHub documentation), those jobs take precedence; you generally do not need to enable automatic dependency submission just to get the Python dependency graph.
- [ ] Check the Dependency graph and Actions tabs if dependency information appears incomplete or stale.

## 4. Dependabot configuration

Create `.github/dependabot.yml` on the **default branch** (Dependabot reads config from the default branch; use `target-branch` if you want PRs against another branch, such as `staging`). Include only package ecosystems and directories that your repository actually uses. Example starter for a repository with root-level Python manifests, a root Dockerfile, and GitHub Actions workflows:

```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
    labels:
      - "dependencies"
      - "python"

  - package-ecosystem: "docker"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 3
    labels:
      - "dependencies"
      - "docker"

  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
    labels:
      - "dependencies"
      - "ci"
```

- [ ] Change directories to match where manifests/Dockerfiles live (for example `/backend`, `/frontend`).
- [ ] Remove ecosystems that are not used; add others (`npm`, `uv`, `pip` in subfolders) only when needed.
- [ ] For monorepos, configure every relevant manifest directory or use the supported multi-directory configuration.
- [ ] Consider `groups:` to batch minor/patch updates into one PR and reduce noise.
- [ ] Commit the file to the default branch and check **Insights → Dependency graph → Dependabot** for status.
- [ ] Review PRs instead of blindly merging them.
- [ ] For ML frameworks, check compatibility among Python, PyTorch/TensorFlow, CUDA, cuDNN, ONNX Runtime, drivers, and deployment images.
- [ ] Prefer small, reviewable update PRs. Avoid unplanned major upgrades in production.
- [ ] Keep a lockfile or pinned/constraints file appropriate to the chosen package manager and application.
- [ ] If a dependency is private, configure access securely; do not place credentials in the YAML file.

## 5. Code scanning and code quality

- [ ] Enable CodeQL default setup if available and suitable.
- [ ] Review findings; determine whether each is a real issue, false positive, or accepted risk.
- [ ] Do not treat "no alerts" as proof that the application is secure.
- [ ] Add linting and formatting (for example, Ruff for Python, ESLint/Prettier for TypeScript) and run them in CI.
- [ ] Add type checking where useful (for example, mypy or pyright, `tsc --noEmit`).
- [ ] Add a Python dependency vulnerability audit in CI (for example `pip-audit`) and `npm audit` for Node projects. Treat results as input for triage, not as automatic failures on day one.
- [ ] Add static security linting for Python (for example Bandit or Ruff's `S` rules).
- [ ] Add tests for authentication, authorization, input validation, file uploads, database access, and other security-sensitive behavior.
- [ ] Avoid executing untrusted code or deserializing untrusted pickle/joblib files.
- [ ] Validate uploads, file paths, URLs, and user-supplied model/data parameters.
- [ ] Keep errors useful for debugging without exposing stack traces, credentials, or internal details to end users.

### 5a. Pre-commit hooks (🤖 agent-doable)

- [ ] Add `.pre-commit-config.yaml` with at least: whitespace/EOF fixers, YAML/JSON checks, large-file check, private-key detection, Ruff (lint + format), and Gitleaks.
- [ ] Document `pre-commit install` in the README/CONTRIBUTING.
- [ ] Run `pre-commit run --all-files` once and commit the resulting fixes in a separate commit.
- [ ] Enforce the same checks in CI so skipping local hooks does not bypass them.

## 6. GitHub Actions and CI/CD security

- [ ] Add a CI workflow to install dependencies and run tests, linting, and relevant checks on pull requests and on pushes to protected branches.
- [ ] Set workflow-level and job-level `permissions` to the minimum required; use read-only (`contents: read`) by default.
- [ ] 👤 Set the repository default workflow token permission to **read-only** (Settings → Actions → General → Workflow permissions).
- [ ] 👤 Require approval for workflows from first-time or all outside contributors (Settings → Actions → General).
- [ ] Avoid exposing secrets to workflows triggered by untrusted fork pull requests.
- [ ] Treat pull-request content, issue comments, branch names, artifacts, and external inputs as untrusted (never interpolate `${{ github.event.* }}` text directly into shell commands).
- [ ] Pin third-party Actions to a full commit SHA for stronger supply-chain protection (Dependabot can keep SHA pins updated); at minimum use trusted, maintained actions and review changes.
- [ ] Avoid running privileged `pull_request_target` workflows on untrusted code or checking out untrusted PR code with secrets.
- [ ] Use GitHub-hosted runners unless self-hosted runners are needed and safely isolated.
- [ ] Do not put secrets in command-line arguments or print them in logs.
- [ ] Use environment protection rules and required reviewers for production deployments where available.
- [ ] Use OIDC for cloud authentication instead of long-lived cloud credentials where supported.
- [ ] Separate test/staging/production credentials and environments.
- [ ] Review third-party Actions and reusable workflows before granting access to secrets or write permissions.
- [ ] Ensure deployment workflows run only on intended branches/tags and events.
- [ ] Set `concurrency` and `timeout-minutes` on workflows so runs cannot pile up or hang forever.
- [ ] Cache dependencies to speed up CI, but never cache secrets or credential files.
- [ ] Check Actions logs and workflow permissions when a job fails or behaves unexpectedly.

### 6a. Minimal CI starter (adapt, do not copy blindly)

```yaml
name: CI
on:
  pull_request:
  push:
    branches: [main, staging]

permissions:
  contents: read

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@v4          # TODO: pin to a full commit SHA
      - uses: actions/setup-python@v5      # TODO: pin to a full commit SHA
        with:
          python-version: "3.11"           # match the version used in production
          cache: "pip"
      - run: pip install -r requirements.txt
      - run: ruff check .
      - run: pytest -q
```

- [ ] Replace the placeholders with the project's real Python version, install command, and test command.
- [ ] Resolve every `TODO: pin` to an exact SHA (verify the SHA belongs to the official action repository).
- [ ] Confirm the workflow passes on a throwaway PR before making it a required check.

## 7. Branch protection, pull requests, and releases (👤 settings, 🤖 docs/templates)

- [ ] Create a ruleset or branch protection rule for `main`/the production branch where appropriate.
- [ ] Require pull requests before merging when working collaboratively or protecting production (for a solo repo, a PR into `main` from `staging` still gives a CI gate and a record).
- [ ] Require CI status checks to pass before merging, once those checks are stable.
- [ ] Consider requiring at least one review for team projects.
- [ ] Block force pushes and branch deletion on important branches unless there is a deliberate reason not to.
- [ ] Keep direct pushes to production limited.
- [ ] Protect release **tags** (a tag ruleset) so published versions cannot be moved or deleted.
- [ ] Use meaningful branch names and commit messages (Conventional Commits are a good default).
- [ ] Review the diff and dependency changes before merging.
- [ ] Tag releases and write release notes for deployed versions.
- [ ] Keep a rollback plan for production deployments (previous tag/commit that is known to work).
- [ ] Do not make required checks mandatory until their exact check names exist and they run reliably.
- [ ] Remember ruleset features and enforcement options vary by GitHub plan and repository visibility.

## 8. Python project setup

- [ ] Choose one primary dependency-management approach (for example, `pyproject.toml` with a supported tool, or `requirements.txt` plus a constraints/lock strategy).
- [ ] Document the supported Python version (and pin it in Dockerfile/CI/hosting config so they agree).
- [ ] Avoid mixing multiple conflicting dependency sources without documenting which one is authoritative.
- [ ] Pin/lock dependencies for reproducible deployment; update them deliberately.
- [ ] Separate runtime dependencies from development/test dependencies where supported (for example `requirements.txt` vs `requirements-dev.txt`).
- [ ] Use a virtual environment locally.
- [ ] Add a clean installation command to the README.
- [ ] Test installation from a fresh environment.
- [ ] Avoid committing `.venv/`, `__pycache__/`, caches, logs, and generated build outputs.
- [ ] Test on the Python versions and operating systems you claim to support.
- [ ] Use a software bill of materials (SBOM) when project risk, deployment requirements, or compliance needs justify it.

## 9. AI/ML, computer vision, LLM, and MLOps checks

- [ ] Document model purpose, intended use, limitations, evaluation metrics, and known failure modes.
- [ ] Document dataset source, license, consent/privacy restrictions, and preprocessing.
- [ ] Keep private or licensed datasets out of Git unless you have permission and a suitable storage plan.
- [ ] Keep large model weights and datasets in appropriate artifact/object storage or Git LFS when justified.
- [ ] Record model version, training configuration, random seeds where relevant, and evaluation procedure.
- [ ] Document Python, framework, CUDA/cuDNN, GPU, driver, and inference-runtime compatibility where applicable.
- [ ] Test model loading and a representative inference request after dependency changes.
- [ ] Test CPU fallback if the application promises it.
- [ ] Avoid loading untrusted pickle/joblib model artifacts; use safer formats (for example safetensors) where practical and verify artifact provenance.
- [ ] Pin model identifiers and revisions (for example a specific Hugging Face revision) so a silent upstream change cannot alter behavior.
- [ ] Treat retrieved documents, prompts, user files, and model outputs as untrusted input.
- [ ] Protect LLM provider keys and vector database credentials.
- [ ] Apply access control to RAG/vector-store data (per-user isolation, tested) and avoid leaking private documents into logs.
- [ ] Check for PII or sensitive data in training samples, evaluation outputs, logs, and notebooks.
- [ ] Evaluate model quality and latency after changes to preprocessing, model runtime, or core ML dependencies.
- [ ] Add an automated **evaluation gate** in CI where practical (for example a small golden set with thresholds) so quality regressions are caught like test failures.
- [ ] Record model/data licensing and third-party model usage restrictions.
- [ ] Do not claim model reproducibility unless the required data, code, environment, and artifacts are actually available.

### 9a. LLM / RAG application security

- [ ] Defend against **prompt injection** (including indirect injection via retrieved documents): keep system instructions separate, never give the model tools or permissions beyond what the feature needs, and never let model output trigger privileged actions without validation.
- [ ] Validate and sanitize model output before rendering it in the UI (avoid raw HTML/Markdown injection) or passing it to a database, shell, or API.
- [ ] Add **rate limits and per-user quotas** on LLM-backed endpoints, plus request size and token limits, to prevent abuse and runaway cost.
- [ ] Set timeouts, retries with backoff, and a graceful fallback message for LLM, embedding, and vector-DB failures.
- [ ] Do not log full prompts, retrieved context, or user documents in production unless required and protected.
- [ ] Test per-user data isolation in the vector store with an automated test (user A must never retrieve user B's chunks).
- [ ] Provide a way to **delete a user's data** (vectors, cached files, logs) and document retention.
- [ ] Keep an eye on provider terms for the data you send (privacy, retention, training use).

## 10. Docker and deployment

- [ ] Use a maintained base image and update it deliberately.
- [ ] Prefer small, trusted base images appropriate for the runtime.
- [ ] Avoid running as root when practical (add a non-root `USER`).
- [ ] Use multi-stage builds when useful to keep production images smaller.
- [ ] Add a `.dockerignore` to exclude secrets, local environments, datasets, caches, and unnecessary files.
- [ ] Never bake credentials into Docker images or image layers.
- [ ] Scan container images for vulnerabilities using a suitable scanner (for example Trivy) in CI.
- [ ] Pin base image versions/digests when reproducibility and risk requirements justify it; establish a process to update them.
- [ ] Configure health checks, graceful shutdown, resource limits, and logging as appropriate.
- [ ] Verify exposed ports and network access.
- [ ] Store production configuration outside the image.
- [ ] Test the final built image, not just the code on the developer's machine.
- [ ] Document deployment, migration, rollback, and backup procedures.
- [ ] Keep staging and production **separate** (separate env vars, keys, and data namespaces/collections) and document how they differ.
- [ ] Confirm the hosting platform's auto-deploy trigger (which branch deploys where) matches your branching strategy.

## 11. API, web application, and database checks

- [ ] Validate all external input and enforce request size/time limits.
- [ ] Use authentication and authorization where needed; do not rely on hidden URLs.
- [ ] Apply least-privilege database credentials.
- [ ] Use parameterized queries/ORM-safe patterns to avoid SQL injection.
- [ ] Use HTTPS in production.
- [ ] Configure CORS narrowly for browser applications (explicit origins, never `*` with credentials); CORS is not authentication.
- [ ] Add security headers on the frontend/backend (for example CSP, `X-Content-Type-Options`, `Referrer-Policy`, HSTS on HTTPS).
- [ ] Add rate limiting and abuse protection where appropriate.
- [ ] Keep production database backups and test restoration.
- [ ] Use migrations for schema changes.
- [ ] Avoid logging passwords, tokens, sensitive personal data, or full private payloads.
- [ ] Configure timeouts, retries, and safe error handling for external services.
- [ ] Keep health/readiness endpoints from leaking sensitive internal details.
- [ ] Never expose server-only secrets to the browser (for Next.js, only `NEXT_PUBLIC_*` variables reach the client, so never put a secret in one).
- [ ] Disable debug mode, interactive docs, and verbose error pages in production if they are not intended to be public.

## 12. Forking someone else's repository

- [ ] Read the original README, contribution guide, license, and security policy.
- [ ] Inspect workflows before running them; do not assume third-party CI is safe.
- [ ] Understand `origin` (usually your fork) and `upstream` (the original repository) if syncing is required.
- [ ] Review repository settings in your fork; not all settings are inherited.
- [ ] Add or adapt your own `.github/dependabot.yml` if you want routine updates.
- [ ] Check whether the original repository's security alerts and workflows apply to your fork.
- [ ] Avoid publishing copied secrets, data, artifacts, or licensed material.
- [ ] Keep your changes on clear feature branches and document how to sync upstream.

## 13. Tests and release readiness

- [ ] Run the test suite locally.
- [ ] Run lint/format/type checks.
- [ ] Build the package/container from a clean checkout.
- [ ] Test key user flows and failure paths.
- [ ] Confirm required environment variables are documented but values are not committed.
- [ ] Review open Dependabot, secret-scanning, and code-scanning alerts.
- [ ] Verify logging and monitoring work (and that errors reach somewhere you will actually look).
- [ ] Verify backup/restore and rollback steps for stateful production systems.
- [ ] Check licenses for key dependencies, datasets, models, and assets.
- [ ] Write release notes, update `CHANGELOG.md`, create the version tag, and identify the deployed commit/version.
- [ ] Smoke-test production after each deploy (health endpoint plus one real end-to-end request).

## 14. Weekly/monthly maintenance

- [ ] Review Dependabot PRs and security alerts.
- [ ] Fix critical/high-risk vulnerabilities promptly, based on actual exposure and exploitability.
- [ ] Investigate failed CI and newly flaky tests.
- [ ] Review stale access tokens, collaborators, GitHub Apps, and cloud permissions.
- [ ] Rotate long-lived API keys on a schedule you can actually keep (for example every 90 days) and immediately after any suspected exposure.
- [ ] Update base images and runtime versions through a tested process.
- [ ] Review dependency changes for compatibility and license impact.
- [ ] Remove unused dependencies and workflows.
- [ ] Check backups, monitoring, provider usage/cost dashboards, and restore procedures for production systems.
- [ ] Update README and operational documentation after meaningful changes.

## 15. GitHub repository settings quick audit (👤)

Open repository **Settings** and review:

- [ ] General: visibility, default branch, features, merge options, auto-delete head branches, and access.
- [ ] Collaborators and teams: least privilege.
- [ ] Rules / branches: protect important branches and release tags.
- [ ] Actions: workflow permissions (read-only default), allowed actions, fork-PR approval, secrets, environments.
- [ ] Security and quality / Code security: dependency graph, Dependabot, secret scanning, push protection, code scanning, private vulnerability reporting.
- [ ] Webhooks and installed apps: remove unneeded integrations.
- [ ] Deploy keys and access tokens: remove stale or overly broad access.
- [ ] Releases and artifacts: avoid publishing secrets or private data.
- [ ] Repository transfer or visibility change: recheck access and security settings afterward.

## 16. Template repository strategy (so you do not forget)

Create one repository such as `ai-ml-project-template` and mark it as a **Template repository** in **Settings → General**.

Include reusable files such as:

```text
.github/
  dependabot.yml
  workflows/
    tests.yml
  PULL_REQUEST_TEMPLATE.md
  CODEOWNERS
.gitignore
.dockerignore
.env.example
.pre-commit-config.yaml
README.md
CHANGELOG.md
PROJECT_SETUP_CHECKLIST.md
SECURITY.md
pyproject.toml
AGENTS.md                 # optional AI-coding-agent instructions
```

- [ ] Use **Use this template** when starting a new project.
- [ ] Copy this checklist into each project.
- [ ] Keep `.github/dependabot.yml` aligned with the project's real ecosystems and directory structure.
- [ ] Verify GitHub settings separately; template files do not copy all repository settings, secrets, protections, or integrations.
- [ ] If using an AI coding assistant, keep tool-specific instructions in the appropriate supported file (`AGENTS.md`, `CLAUDE.md`, `SKILL.md`, or other documented format) and point it at Section A of this file. These files do not switch on GitHub security features by themselves.
- [ ] Periodically update the template and test it by creating a throwaway repository from it.

## 17. Suggested minimum setup for a solo developer

If you are overwhelmed, do these first:

1. [ ] `.gitignore` + no secrets in Git.
2. [ ] README + dependency manifest/lock strategy.
3. [ ] Dependency graph + Dependabot alerts.
4. [ ] Dependabot security updates where available.
5. [ ] `.github/dependabot.yml` for the package managers actually used.
6. [ ] Secret scanning and push protection where available; Gitleaks locally/CI if useful.
7. [ ] Basic GitHub Actions tests.
8. [ ] CodeQL if available and appropriate.
9. [ ] Protect `main` for collaborative/production repositories.
10. [ ] 2FA/passkeys on GitHub and every provider account; usage limits on every paid API key.
11. [ ] Copy this checklist into the repository and review it before deployment.

---

## Appendix A. ChessCoach AI specifics (repo: `dasharatha19/Chesscoach-main`)

Context: RAG-based chess coach that analyzes a user's own Chess.com games. FastAPI backend on Render, Next.js frontend on Vercel, Qdrant Cloud (per-user collections), Groq (LLM), Hugging Face Inference API (embeddings, `BAAI/bge-small-en-v1.5`). Branches: `main` (production) and `staging` (pre-prod). Docs kept in-repo: `ROADMAP.md`, `CHANGELOG.md`, `TODO.md`.

Apply the generic sections above, plus:

**Branching and agent workflow**
- [ ] Agent work lands on `staging` via PR; only the human merges `staging` → `main` as a versioned release (changelog entry + git tag).
- [ ] `dependabot.yml` uses `target-branch: "staging"` for version updates so updates are tested before production.
- [ ] CI runs on PRs and on pushes to both `staging` and `main`.

**Dependabot for this repo's layout** (adjust directories to the real structure)

```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/backend"          # adjust to where requirements.txt / pyproject.toml lives
    target-branch: "staging"
    schedule:
      interval: "weekly"
    groups:
      python-minor-patch:
        update-types: ["minor", "patch"]
    labels: ["dependencies", "python"]

  - package-ecosystem: "npm"
    directory: "/frontend"         # adjust to where package.json lives
    target-branch: "staging"
    schedule:
      interval: "weekly"
    groups:
      npm-minor-patch:
        update-types: ["minor", "patch"]
    labels: ["dependencies", "javascript"]

  - package-ecosystem: "github-actions"
    directory: "/"
    target-branch: "staging"
    schedule:
      interval: "weekly"
    labels: ["dependencies", "ci"]
```

- [ ] Add a `docker` entry only if a Dockerfile actually exists.
- [ ] Note: security-update PRs target the default branch regardless; version-update PRs follow `target-branch`.

**Secrets and keys** (never commit; document names only in `.env.example`)
- [ ] `.env.example` lists every variable used (Groq key, Hugging Face token, Qdrant URL and API key, any CORS/origin settings, environment name) with placeholders.
- [ ] 👤 Separate keys for staging and production where the provider allows it; usage limits set on the Groq and Hugging Face keys.
- [ ] 👤 Render and Vercel env vars set per environment; no secrets in `NEXT_PUBLIC_*` variables.
- [ ] 👤 Qdrant Cloud API key scoped as narrowly as the plan allows.

**Qdrant / environment isolation**
- [ ] Collection-name prefixes (`prod_` vs `staging_`) enforced **in code from an environment variable**, so staging can never write to production collections by accident.
- [ ] Automated test: user A can never retrieve user B's chunks (per-user collections).
- [ ] A documented "delete my data" path that removes a user's collection and any cached game data.

**LLM / RAG hardening**
- [ ] Chess.com game text (PGN, comments, usernames) is treated as untrusted input when placed into prompts (prompt-injection and output-sanitization checks from Section 9a).
- [ ] Rate limits and per-user quotas on the chat/analysis endpoints; request size limits on game imports.
- [ ] Timeouts, retries with backoff, and friendly fallbacks for Groq, Hugging Face Inference, and Qdrant failures (the Render free tier and free inference tiers are rate-limited and can cold-start).
- [ ] Pin the embedding model name and revision; changing the embedding model requires re-indexing and must be a deliberate, documented migration.
- [ ] Confirm Chess.com data usage follows their terms and any public API guidelines (rate limits, caching, attribution), and that only the user's own games are indexed.
- [ ] If Stockfish or other engines are used or distributed, check their license obligations (Stockfish is GPLv3).

**Evaluation and CI**
- [ ] DeepEval tests run in pytest in CI. Keep a small, cheap "smoke" evaluation set in CI and heavier evaluations manual/scheduled, so CI stays fast and does not burn LLM quota.
- [ ] LLM-judged evaluations need API keys: expose them only to trusted workflows (never to fork PRs).

**Deploy and operations**
- [ ] 👤 Confirm which branch each platform auto-deploys (`main` → production, `staging` → pre-prod) on both Render and Vercel.
- [ ] Health endpoint exists and is used for uptime checks; post-deploy smoke test documented.
- [ ] `WEB_CONCURRENCY=1` on Render is documented in the README with the reason (memory limit) and the trigger for revisiting it (measured load).
- [ ] Release process documented: merge `staging` → `main`, update `CHANGELOG.md`, tag version, verify production, note rollback target.
- [ ] CORS allows only the real Vercel production and staging origins.

---

## Appendix B. Progress log (agent and human fill this in)

| Date | Who | What changed (PR / commit) | Left for human |
|---|---|---|---|
| | | | |

---

## Official documentation

Use official documentation for current behavior, configuration, and plan limitations:

- [GitHub quickstart: securing your repository](https://docs.github.com/en/code-security/getting-started/quickstart-for-securing-your-repository)
- [Dependency graph](https://docs.github.com/en/code-security/supply-chain-security/understanding-your-software-supply-chain/about-the-dependency-graph)
- [Dependabot alerts](https://docs.github.com/en/code-security/concepts/supply-chain-security/dependabot-alerts)
- [Dependabot security updates](https://docs.github.com/en/code-security/dependabot/dependabot-security-updates/about-dependabot-security-updates)
- [Configure Dependabot version updates](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/secure-your-dependencies/configure-version-updates)
- [Dependabot configuration reference](https://docs.github.com/en/code-security/dependabot/dependabot-version-updates/configuration-options-for-the-dependabot.yml-file)
- [Automatic dependency submission](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/secure-your-dependencies/submit-dependencies-automatically)
- [Secret scanning](https://docs.github.com/en/code-security/secret-scanning/introduction/about-secret-scanning)
- [Push protection](https://docs.github.com/en/code-security/secret-scanning/introduction/about-push-protection)
- [Code scanning / CodeQL](https://docs.github.com/en/code-security/code-scanning/introduction-to-code-scanning/about-code-scanning)
- [Secure use of GitHub Actions](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions)
- [Repository rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)
- [Create a template repository](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-template-repository)
- [OWASP Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/)

**Final rule:** automate repeatable checks, keep credentials out of Git, review security alerts, and test dependency updates before merging. No checklist or scanner replaces code review and good operational practices.
