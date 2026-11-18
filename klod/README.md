# KLOD

Klod is an independent AI platform under active development. This milestone contains an exact-round-trip byte-level BPE tokenizer, a decoder-only Transformer with RoPE, a resumable next-token trainer, a guarded FastAPI inference service and a mobile-first React interface.

**Status:** experimental foundation. No production model, production login, database, live agents, hosted service or APK is claimed to exist yet.

## Structure

- backend/klod/tokenizer: byte-level BPE and versioned vocabulary.
- backend/klod/neural: decoder-only Transformer, causal attention and RoPE.
- backend/klod/training: dataset loader, AdamW, gradient clipping, scheduler and checkpoints.
- backend/klod/api: model status and guarded generation API.
- backend/tests: automated tests.
- frontend: React + TypeScript + Vite mobile-first interface.
- docs: architecture, security and progress ledger.

## Requirements

Python 3.10+, PyTorch 2.14.1, Node.js 20.19+ or 22.12+ for Vite 8. Capacitor 8 requires Node.js 22+ and Android SDK API 24+.

## Backend

Create a virtual environment, then install this project with the dev extra: python -m pip install -e '.[dev]'. Run tests with pytest. Train on properly licensed text with: python -m klod.training.train --dataset data/train.jsonl --steps 1000 --seq-len 128 --vocab-size 2048. JSONL records must contain a string text field. The first run saves artifacts/tokenizer.json; checkpoints are stored under artifacts/checkpoints/.

Run the API with: uvicorn klod.api.main:app --host 0.0.0.0 --port 8000. It returns HTTP 503 for generation until a compatible tokenizer and checkpoint with at least one optimizer update exist.

## Frontend

Run npm install and npm run dev from frontend/. Set VITE_KLOD_API_URL if the API uses another origin. The interface does not fabricate model responses when the service is offline.

## Release gates

Terminal access, file editing, production OAuth, user administration, real multi-agent tools and Android packaging are deferred. APK generation remains blocked until the twelve required UI validations have evidence, each scores at least 8/10 and their average is at least 8.5/10.