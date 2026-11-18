# KLOD

Klod is an original, mobile-first AI platform under active development. It is designed as **one AI and one agent identity**: one project-owned neural model, one continuous context and decision process, and one integrated coder capability. Claude Fable 5.2, Claude Opus 5.5 and Claude Code are public-facing capability references, not models, weights, prompts or private systems loaded into Klod.

**Status:** experimental foundation. The tokenizer, decoder-only neural architecture, training pipeline, checkpoint loading, Google identity code, mobile web interface and first single-agent/coder interfaces are implemented. This is not a production-trained assistant. The coder's file workspace is not yet exposed as an interactive web/API tool, and no unrestricted terminal is enabled.

## Repository layout

- backend/klod/tokenizer: versioned byte-level BPE with exact UTF-8 reconstruction and append-only expansion.
- backend/klod/neural: one decoder-only Transformer model with causal attention and RoPE.
- backend/klod/training: corpus loading, train/validation split, AdamW, clipping, scheduler, checkpoints and model expansion.
- backend/klod/agent.py: the single Klod identity and its unified runtime.
- backend/klod/tools: integrated coder workspace capabilities, guarded by permissions and per-file approvals.
- backend/klod/api: FastAPI model, chat, authentication and admin routes.
- backend/klod/auth: Google token verification and PostgreSQL session storage.
- backend/migrations: PostgreSQL schema.
- backend/tests: tokenizer, neural expansion, training, API, agent and authentication tests.
- frontend: mobile-first React, PWA and Capacitor configuration.
- docs: architecture, expansion, security, validation gates and development ledger.

## Language and tokenizer coverage

Klod uses UTF-8 byte-level BPE. The base byte vocabulary can encode every valid Unicode scalar value representable in UTF-8, including scripts not present in the training corpus, combining marks, right-to-left text, emoji, mathematical symbols, punctuation, whitespace, programming operators and delimiters.

The tokenizer does not normalize text. This is deliberate: distinct Unicode sequences are preserved exactly, including decomposed and precomposed accents. BPE merges are learned from the actual authorized training corpus. Therefore, representation coverage is universal for valid UTF-8 input, but language understanding and generation quality still depend on the model architecture, training data and evaluation. A tokenizable language is not automatically a language the model understands.

Default vocabulary target: 32,768 IDs, including reserved special tokens. This is a target rather than a promise: if the corpus does not contain enough repeated pairs at the configured minimum frequency, training stops below the target. See docs/TOKENIZER_EXPANSION.md.

## Requirements

Python 3.10+, PyTorch 2.14.1, Node.js 22+ for Capacitor 8, and PostgreSQL 14+ recommended.

## Backend setup

From the klod directory:

    python -m venv .venv
    . .venv/bin/activate
    python -m pip install --upgrade pip
    python -m pip install -e '.[dev]'
    pytest

Train a fresh experimental model with an authorized text or JSONL corpus. JSONL records must contain a string text field:

    python -m klod.training.train --dataset data/train.jsonl --output-dir artifacts/v1 --steps 5000 --seq-len 128 --vocab-size 32768 --device auto

The tokenizer is saved under artifacts/v1/tokenizer.json; checkpoints are stored under artifacts/v1/checkpoints/. A small training run proves that optimization executed, not that conversational quality has been achieved.

## Periodic model and tokenizer expansion

Expand from a compatible prior checkpoint instead of overwriting it:

    python -m klod.training.train --dataset data/new-corpus.jsonl --output-dir artifacts/v2 --tokenizer artifacts/v1/tokenizer.json --expand-tokenizer --expand-from artifacts/v1/checkpoints/latest.pt --vocab-size 65536 --seq-len 256 --n-layers 6 --d-ff 1536 --steps 20000

The new run keeps existing tokenizer IDs and special-token IDs stable, copies old neural weights into the larger model, appends new Transformer layers and starts a fresh optimizer for the expanded parameter shapes. The parent checkpoint remains untouched. The actual vocabulary size is recorded in the logs and checkpoint; it may remain below the requested target if the corpus lacks enough repeated pairs.

Safe expansion currently preserves model width and attention-head count. It can increase vocabulary size, context length, Transformer depth and feed-forward width. Changing d_model or n_heads requires a separately designed architecture migration and is rejected rather than silently reshaping weights. See docs/MODEL_EXPANSION.md.

Use --resume to continue an exactly matching model and tokenizer, preserving optimizer and scheduler state. Do not combine --retrain-tokenizer with resume or expansion: retraining from scratch changes token IDs and invalidates existing checkpoints.

A reproducible CPU smoke test using the original CC0 demo corpus is:

    python -m klod.training.train --dataset data/demo_corpus.txt --output-dir artifacts/demo --steps 60 --seq-len 48 --vocab-size 320 --d-model 64 --n-heads 4 --n-layers 2 --d-ff 128 --batch-size 4 --learning-rate 0.002 --warmup-steps 5 --val-fraction 0.1 --eval-every 10 --eval-batches 10 --checkpoint-every 20 --log-every 10 --device cpu

The observed metrics and incoherent sample output are recorded in docs/DEMO_TRAINING.md. This is not a production model.

## Google authentication and PostgreSQL

Create a Google OAuth 2.0 Web client and register the exact frontend JavaScript origins. Set GOOGLE_CLIENT_ID, DATABASE_URL and VITE_GOOGLE_CLIENT_ID in the appropriate backend/frontend environments. Apply the initial schema:

    psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f backend/migrations/001_identity.sql

The backend verifies Google ID tokens server-side, requires verified email identity, uses sub as the stable identity key, stores only hashes of opaque session tokens, issues HttpOnly session cookies and checks CSRF on cookie-authenticated writes. First-admin assignment locks the singleton platform-state row in a PostgreSQL transaction. Chat and admin endpoints require a valid session and admin access is enforced by the backend.

For local HTTP development only, set KLOD_SESSION_COOKIE_SECURE=false. Use KLOD_COOKIE_SAMESITE=lax when the frontend and API are same-site. For cross-site hosts, configure KLOD_COOKIE_SAMESITE=none with Secure cookies and exact CORS origins. Never commit credentials or place secrets in VITE variables.

Start the API:

    uvicorn klod.api.main:app --host 0.0.0.0 --port 8000

Generation returns HTTP 503 until a compatible tokenizer and checkpoint with at least one optimizer update exist. Google login remains disabled until the OAuth client ID, database and migration are configured.

## Frontend and PWA

    cd frontend
    npm install
    npm run dev

Set VITE_KLOD_API_URL when the backend has another origin. VITE_GOOGLE_CLIENT_ID enables the Google Identity Services sign-in button. The PWA caches static assets, not API responses.

## Deployment and release gates

GitHub Actions tests the backend and builds the frontend on klod-development. The frontend root for Vercel is klod/frontend; neural training/inference workers need suitable compute, not short-lived serverless functions.

The current coder workspace supports path-confined text reads and writes with explicit permissions and exact-path approval. It is not yet wired to the web interface or public coder API. No host shell execution is enabled. Conversation persistence, full admin dashboard, research retrieval, real terminal sandbox, project Git operations, distributed rate limiting, monitoring and public deployment remain incomplete.

APK generation remains blocked until all twelve requested UI/functionality validations have genuine evidence, each scores at least 8/10 and the average is at least 8.5/10.
