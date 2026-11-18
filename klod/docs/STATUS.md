# Development ledger — 2026-11-18

## Implemented

- Klod lives in the isolated klod/ directory on klod-development; existing main-branch projects are preserved.
- One user-facing Klod agent class and one neural runtime. Coder functionality is modeled as an integrated workspace capability, not a separate agent.
- Byte-level BPE tokenizer format v3 with reserved special-token IDs, append-only expansion, exact UTF-8 reconstruction, merge-frequency metadata and v2 compatibility.
- Tokenizer tests for Portuguese, English, multiple Unicode writing systems, combining marks, bidi marks, emoji, punctuation, operators, code, whitespace and unseen text.
- Decoder-only Transformer with RoPE, causal multi-head attention, tied input/output embeddings, RMSNorm, residual blocks, GELU feed-forward network and next-token loss.
- Safe neural expansion for vocabulary, context length, depth and feed-forward width while preserving old-token logits at initialization. d_model/head-count changes are rejected pending a separately validated migration.
- AdamW training, gradient clipping, warmup/cosine scheduler, chronological train/validation split, atomic checkpoints, exact resume and lineage-preserving model expansion.
- FastAPI model/chat/auth/admin routes; Google ID token verification; PostgreSQL identity/session schema; hashed opaque sessions, HttpOnly cookies and CSRF checks on chat/logout.
- Transactional first-admin assignment under a PostgreSQL singleton-row lock.
- Mobile-first React interface, Google Identity Services sign-in UI when configured, PWA manifest and Service Worker; Capacitor 8 config.
- GitHub Actions CI for backend tests and frontend production build.

## Validation evidence

- Earlier baseline CI run 44220033687 passed both backend and frontend before the later CSRF enforcement change.
- CI run 44220205476: frontend build passed; backend had 23 passing tests and one failure. The failure was a stale test expecting chat to reach model inference without the new mandatory CSRF token; a follow-up test and frontend header correction are included in the current changes.
- The current tokenizer/model expansion changes are awaiting a new CI run; do not mark them passed until that run finishes.
- Prior local training evidence: 60 CPU updates, 86,720 parameters, 320-token vocabulary; step-60 validation loss 4.4094242 and incoherent generated text. This demonstrated the training and inference path only, not language competence.

## Not implemented or not yet validated

- Large, licensed multilingual corpus and production-quality model training.
- Full benchmark suite for multilingual comprehension, reasoning, math, coding and tool use.
- Production Google OAuth credentials, PostgreSQL provisioning and end-to-end authentication in a deployed environment.
- Fully exposed coder interface, code diff review, Git operations and isolated terminal execution.
- Persistent conversations/projects, full admin dashboard, research retrieval and tool-use training.
- Distributed rate limiting, observability, backups, incident recovery and public deployment.
- Twelve independently evidenced UI confirmations; no similarity scores have been assigned.
- Capacitor Android project generation, APK compilation, signing and device tests.

## Release gate

APK generation remains blocked until all twelve confirmations have real evidence, each is at least 8/10 and their average is at least 8.5/10. No gate is passed from source inspection alone.
