# KLOD

Original mobile-first AI platform. This implementation lives in its own directory and preserves all existing repository projects.

## Status
Engineering foundation only. The web interface, API skeleton, byte-level BPE tokenizer and experimental decoder-only Transformer are source implementations. No trained assistant checkpoint, Google OAuth deployment, production database, agent execution sandbox, or Android release is claimed.

## Layout
- backend/ — FastAPI, tokenizer, neural model and training entry point
- web/ — React + TypeScript + Vite interface
- docs/ — architecture and release gates
- .github/workflows/ — CI

## Local checks
Backend: Python 3.11+, install backend with dev extras and run pytest.
Web: Node 22+, run npm install and npm run build from web/.

Never commit secrets, private datasets or model checkpoints. Android packaging remains blocked until the twelve confirmations in docs/VALIDATION.md have real evidence.
