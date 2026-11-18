# KLOD

Klod is an independent AI platform under active development. This engineering slice includes a project-owned byte-level BPE tokenizer, a decoder-only Transformer with RoPE, a next-token training loop, resumable checkpoints, a guarded FastAPI service, a mobile-first React interface, a PWA shell, and initial Google identity/session code.

**Status:** experimental foundation. No production-trained language model, live production database, verified production OAuth deployment, hosted service, agent execution environment, or Android APK is claimed to exist.

## Repository layout

- backend/klod/tokenizer: byte-level BPE with exact UTF-8 reconstruction.
- backend/klod/neural: decoder-only Transformer with causal attention and RoPE.
- backend/klod/training: corpus loading, train/validation split, AdamW, clipping, scheduler and checkpoints.
- backend/klod/api: FastAPI model, chat, authentication and admin routes.
- backend/klod/auth: Google token verification and PostgreSQL session storage.
- backend/migrations: PostgreSQL schema.
- backend/tests: tokenizer, model, training, API and authentication tests.
- frontend: mobile-first React, PWA and Capacitor configuration.
- docs: architecture, security and development ledger.

## Requirements

Python 3.10+, PyTorch 2.14.1, Node.js 22+ for Capacitor 8, and PostgreSQL 14+ recommended.

## Backend setup

From the klod directory:

    python -m venv .venv
    . .venv/bin/activate
    python -m pip install --upgrade pip
    python -m pip install -e '.[dev]'
    pytest

Train an experimental model with a properly licensed text or JSONL corpus. JSONL records must contain a string text field:

    python -m klod.training.train --dataset data/train.jsonl --steps 1000 --seq-len 128 --vocab-size 2048

The tokenizer is saved under artifacts/tokenizer.json; checkpoints are stored under artifacts/checkpoints/. A short training run proves that optimization executed, not that conversational quality has been achieved.

## Google authentication and PostgreSQL

Create a Google OAuth 2.0 Web client and register the exact frontend JavaScript origins. Set GOOGLE_CLIENT_ID, DATABASE_URL and VITE_GOOGLE_CLIENT_ID in the appropriate backend/frontend environments. Apply the initial schema:

    psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f backend/migrations/001_identity.sql

The backend verifies Google ID tokens server-side, requires verified email identity, uses sub as the stable identity key, stores only hashes of opaque session tokens, issues HttpOnly session cookies and checks a CSRF token on logout. First-admin assignment locks the singleton platform-state row in a PostgreSQL transaction. Chat and admin endpoints require a valid session and admin access is enforced by the backend.

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

The development terminal, project filesystem editing, real agents, conversation persistence, full admin dashboard, distributed rate limiting and Android-native packaging are not complete. APK generation remains blocked until all twelve requested UI/functionality validations have genuine evidence, each scores at least 8/10 and the average is at least 8.5/10.
