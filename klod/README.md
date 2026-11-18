# KLOD

Klod is an original, mobile-first AI platform under active development. It is designed as **one AI and one agent identity**: one project-owned neural model, one continuous context and decision process, and one integrated coder capability. Claude Fable 5.2, Claude Opus 5.5 and Claude Code are public capability references only; their models, weights, prompts and private systems are not loaded into Klod.

**Current status:** experimental implementation with an automated PostgreSQL integration suite and Playwright browser acceptance tests. The application has a persistent conversation UI, project management, an integrated text-file coder workspace and an admin dashboard. Production Google OAuth credentials, a production database, a trained production-quality checkpoint, a public deployment and a signed release APK are not supplied. The coder does not execute commands on the host and is not an unrestricted terminal.

## Architecture

- `backend/klod/agent.py`: one `KlodAgent` identity and one neural runtime. Coder functions are capabilities on that same agent.
- `backend/klod/tokenizer`: versioned byte-level BPE; UTF-8 byte coverage and append-only vocabulary expansion.
- `backend/klod/neural`: one decoder-only Transformer with causal attention and RoPE.
- `backend/klod/training`: corpus loading, train/validation split, AdamW, clipping, scheduler, checkpoints, exact resume and safe expansion.
- `backend/klod/auth`: server-side Google ID-token verification and PostgreSQL sessions.
- `backend/klod/api`: FastAPI auth, chat, conversations, projects, workspace and admin endpoints.
- `backend/klod/tools/workspace.py`: per-user and per-project path-confined file workspace, explicit write permission and atomic file writes.
- `backend/migrations`: PostgreSQL schema.
- `backend/tests`: tokenizer, neural training/inference, API, authentication, workspace isolation and PostgreSQL integration tests.
- `frontend`: mobile-first React, TypeScript, Vite, PWA, Playwright acceptance suite and Capacitor Android configuration.
- `docs/release-evidence.json`: the 12 independently evidenced release confirmations. No score may be assigned from source inspection alone.

## Unicode and tokenizer

Klod uses UTF-8 byte-level BPE. The base byte vocabulary can represent every valid Unicode scalar value encoded as UTF-8, including scripts not present in the training corpus, combining marks, right-to-left text, emoji, mathematical symbols, punctuation, whitespace, programming operators and delimiters.

The tokenizer does not normalize text, so distinct Unicode sequences are preserved exactly. BPE merges are learned from the authorized training corpus. Universal byte representation does not imply universal language understanding; comprehension and generation depend on model capacity, training data and evaluation.

Default vocabulary target: 32,768 IDs including reserved special tokens. It is a target, not a promise: if the corpus lacks enough repeated pairs at the configured minimum frequency, training stops below the target.

## Requirements

- Python 3.10+
- PyTorch version pinned in `pyproject.toml`
- Node.js 22+ for Capacitor 8 and the frontend toolchain
- PostgreSQL 14+ recommended (CI integration service uses PostgreSQL 16)
- Android SDK and JDK versions documented in the Android release workflow

## Backend setup

From the `klod` directory:

    python -m venv .venv
    . .venv/bin/activate
    python -m pip install --upgrade pip
    python -m pip install -e '.[dev]'
    pytest -q

Apply both database migrations in order:

    psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f backend/migrations/001_identity.sql
    psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f backend/migrations/002_conversations_projects.sql

Configure `GOOGLE_CLIENT_ID`, `DATABASE_URL`, `KLOD_CORS_ORIGINS`, `KLOD_SESSION_COOKIE_SECURE` and `KLOD_COOKIE_SAMESITE` on the API. Configure `VITE_GOOGLE_CLIENT_ID` and, when the API uses a separate origin, `VITE_KLOD_API_URL` for the frontend. Never commit credentials or put server secrets in Vite variables.

Start the API:

    uvicorn klod.api.main:app --host 0.0.0.0 --port 8000

The Google login route verifies the signed ID token on the server. The first identity transactionally assigned as owner becomes the administrator. Session tokens are opaque, stored as hashes and delivered in HttpOnly cookies. Cookie-authenticated state changes require CSRF validation.

## API overview

- `GET /health` and `GET /v1/model`: service and checkpoint status.
- `POST /v1/auth/google`, `GET /v1/auth/me`, `POST /v1/auth/logout`: identity and session lifecycle.
- `POST /v1/chat`: model inference and persistent user/assistant messages. Requires a valid session and CSRF header.
- `GET/POST /v1/conversations`, `GET /v1/conversations/{id}`: conversation history.
- `GET/POST /v1/projects`: project list and creation.
- `GET/PUT /v1/projects/{id}/files`: list, read and save text files inside the authenticated user's project workspace.
- `GET /v1/admin/overview`, `GET /v1/admin/users`: server-authorized administration endpoints.

The API rejects inference with HTTP 503 until a compatible tokenizer and checkpoint containing at least one optimizer update are configured. A working training smoke test does not certify production language competence.

## Training and expansion

Train a fresh experimental model with an authorized text or JSONL corpus. JSONL records must contain a string `text` field:

    python -m klod.training.train --dataset data/train.jsonl --output-dir artifacts/v1 --steps 5000 --seq-len 128 --vocab-size 32768 --device auto

The tokenizer is saved under `artifacts/v1/tokenizer.json`; checkpoints are stored under `artifacts/v1/checkpoints/`. A small run proves optimization and checkpoint execution only, not high-quality conversation.

Expand from a compatible parent checkpoint rather than overwriting it:

    python -m klod.training.train --dataset data/new-corpus.jsonl --output-dir artifacts/v2 --tokenizer artifacts/v1/tokenizer.json --expand-tokenizer --expand-from artifacts/v1/checkpoints/latest.pt --vocab-size 65536 --seq-len 256 --n-layers 6 --d-ff 1536 --steps 20000

Existing tokenizer IDs and special-token IDs remain stable. The parent checkpoint remains unchanged. Safe expansion can increase vocabulary size, context length, Transformer depth and feed-forward width. Changing `d_model` or `n_heads` requires a separately validated architecture migration.

Use `--resume` only with an exactly matching model and tokenizer. Do not combine `--retrain-tokenizer` with resume or expansion because new token IDs invalidate old checkpoints.

A reproducible CPU smoke test is documented in `docs/DEMO_TRAINING.md`; its incoherent generated output is explicitly not considered a production model.

## Frontend, browser tests and PWA

    cd frontend
    npm install
    npm run dev

Build and test:

    npm run build
    npx playwright install chromium
    npm run test:e2e

The Playwright suite checks mobile and desktop layout, navigation, conversation restoration, project creation, coder file saving, admin display and chat submission through controlled API fixtures. PostgreSQL integration tests run against a real service in GitHub Actions.

## Android release process

Capacitor is configured in `frontend/capacitor.config.ts`. The native Android directory is generated by the guarded GitHub Actions candidate workflow; it is not treated as an existing deliverable.

The workflow's manual `build_android_candidate` input is disabled by default. It requires backend tests, frontend build, browser acceptance tests and evidence for confirmations 1–11 to pass before generating a debug APK, installing it on an Android emulator and uploading APK plus screenshot evidence. It does not produce a production-signed release. A production signing configuration and final device acceptance are separate release tasks.

Run the release checker locally from repository root:

    python klod/scripts/release_gate.py --through 11
    python klod/scripts/release_gate.py --through 12

Each confirmation needs an evidence reference, status `pass`, score at least 8/10 and the overall average must be at least 8.5/10. Do not alter scores to force release.

## Known limitations

- Production OAuth credentials, live external Google sign-in and production PostgreSQL provisioning still require configuration and real-environment testing.
- No production-trained multilingual model/checkpoint or capability benchmark suite is currently shipped.
- The coder currently supports safe text-file operations only; no shell runner, Git operations or unrestricted terminal is enabled.
- Conversation and project storage require applying both SQL migrations.
- Public deployment, distributed rate limiting, observability, backup/restore and incident recovery remain operational tasks.
- A browser viewport test is not a physical-device test. APK generation and emulator installation are separate, guarded release confirmations.
