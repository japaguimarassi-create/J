# Development ledger — 2026-11-17

## Implemented in the foundation

- Dedicated klod-development branch created from main; original content untouched.
- Project directory isolated under klod/.
- Byte-level BPE tokenizer, versioned persistence and exact UTF-8 round-trip tests.
- Decoder-only Transformer with RoPE, causal multi-head attention, residual blocks and next-token loss.
- Real AdamW training loop, gradient clipping, warmup/cosine scheduling, chronological train/validation split, validation loss and atomic resumable checkpoints.
- FastAPI health, model status and guarded inference endpoints.
- Mobile-first React frontend with a PWA manifest, service worker and truthful offline/model-unavailable state.
- GitHub Actions pipeline for Python tests and frontend build.

## Validation evidence

- Local Python suite: 8 tests passing on PyTorch 2.10.0+cpu.
- Frontend GitHub Actions job: PASS on Node 22, dependency installation and Vite/TypeScript production build.
- Backend GitHub Actions job: first run was still installing the pinned PyTorch dependency at the time of this update; a completed remote result is required before claiming CI pass.
- Local npm dependency installation hit a timeout in this execution environment; the remote frontend CI job completed successfully instead.

## Not implemented

Production Google OAuth and sessions; PostgreSQL migrations and atomic first-admin bootstrap; admin panel; real agent orchestration; isolated terminal and project-file operations; large licensed corpus; benchmarked model quality; production deployment; twelve evidence-backed UI confirmations; Android build/signing/device tests.

APK generation remains blocked until every confirmation is evidenced, each scores at least 8/10 and the average is at least 8.5/10.