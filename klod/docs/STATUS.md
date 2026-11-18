# Development ledger — 2026-11-17

## Implemented

- Dedicated klod-development branch; original main and unrelated projects left untouched.
- Isolated klod/ product directory.
- Byte-level BPE tokenizer with versioned persistence and exact UTF-8 round-trip tests.
- Decoder-only Transformer with RoPE, causal multi-head attention, tied token/output embeddings, RMSNorm, residual blocks, GELU feed-forward network and next-token loss.
- Real AdamW training loop, gradient clipping, warmup/cosine scheduler, chronological train/validation split, validation loss and atomic resumable checkpoints.
- FastAPI model health/status and chat endpoints; chat requires a valid user session and refuses generation without a trained checkpoint.
- Google ID token verification, PostgreSQL identity/session schema, hashed opaque sessions, HttpOnly session cookie, CSRF-protected logout and server-side admin user listing.
- Transactional first-admin selection under a PostgreSQL singleton-row lock.
- Mobile-first React interface, Google Identity Services sign-in UI when VITE_GOOGLE_CLIENT_ID is configured, PWA manifest and static-asset Service Worker.
- Capacitor 8 configuration and GitHub Actions workflow for backend tests and frontend production build.

## Validation evidence

- Local suite: 17 passed on Python 3.13.5 and PyTorch 2.10.0+cpu. The project pins PyTorch 2.14.1; exact pinned runtime must be validated separately in CI.
- python -m compileall -q backend: passed locally.
- GitHub Actions run 44206245598 on commit 08d426f: backend and frontend jobs completed successfully.
- GitHub Actions run 44206821260 on commit 924a009: frontend job passed; backend was still installing pinned PyTorch at last inspection.
- Vercel preview creation returned HTTP 429 due to GitHub API rate limiting. No deployed URL is available.
- Google OAuth and PostgreSQL code/schema exist, but production OAuth client ID and a live database are not configured; end-to-end login and admin bootstrap remain unverified.
- Local npm installation timed out; remote frontend CI build passed.

## Not implemented or not yet validated

- Production-trained or benchmarked conversational model; no large licensed corpus has been trained.
- Production OAuth credentials, PostgreSQL provisioning and end-to-end login/session tests.
- Full admin dashboard, conversation persistence and project persistence.
- Real multi-agent planner, research connectors, isolated terminal/filesystem worker, Git execution and approval/diff workflow.
- Production rate limiting, monitoring, backups, incident recovery and public deployment.
- Twelve independently evidenced UI confirmations; no screenshot-based similarity scores have been assigned.
- Capacitor Android platform generation, APK compilation, signing and device tests.

## Release gate

APK generation remains blocked until all twelve confirmations have real evidence, each scores at least 8/10 and their average is at least 8.5/10. No gate is passed from source inspection alone.
