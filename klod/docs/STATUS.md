# Development ledger — 2026-11-18

## Current repository state

- Klod remains isolated in `klod/` on `klod-development`; existing projects on other branches are untouched.
- Latest implementation commit: `fd7382a4165f5713a5ea4bdebed8f14db148b885`.
- GitHub Actions run `44241830519` completed with conclusion `success`.
  - Frontend: dependency installation and mobile-first production build passed.
  - Backend: dependency installation and full pytest suite passed.
  - Workflow URL: https://github.com/japaguimarassi-create/J/actions/runs/44241830519
- That workflow published zero artifacts. It did not build an Android package.
- CI verifies buildability and automated backend tests. It is not a visual/device acceptance test.
- The main React class names and stylesheet selectors have been aligned in commit `fd7382a`. The rendered appearance still requires screenshot/device verification.

## Implemented foundation

- One user-facing `KlodAgent` and one neural runtime. Coder is an integrated capability, not another agent.
- Byte-level BPE tokenizer format v3 with reserved special-token IDs, append-only expansion, exact UTF-8 reconstruction, merge-frequency metadata and v2 compatibility.
- Unicode segmentation/coverage reports and tests for Portuguese, English, CJK, Arabic, Hebrew, Indic scripts, combining marks, mathematical symbols, emoji, punctuation, controls and whitespace.
- Decoder-only Transformer with RoPE, causal multi-head attention, tied embeddings, RMSNorm, residual blocks, GELU feed-forward network and next-token loss.
- Safe neural expansion for vocabulary, context length, depth and feed-forward width. Model width/head-count changes remain rejected pending a separately validated migration.
- AdamW training, gradient clipping, warmup/cosine scheduler, chronological train/validation split, atomic checkpoints, exact resume and checkpoint lineage.
- FastAPI chat/auth/admin routes; server-side Google ID token verification; PostgreSQL identity/session schema; hashed opaque sessions, HttpOnly cookies and CSRF checks on chat/logout.
- Transactional first-admin assignment under a PostgreSQL singleton-row lock.
- React + TypeScript + Vite mobile-first client, PWA manifest/service worker and Capacitor 8 configuration.
- GitHub Actions CI for backend tests and frontend production build.

## Twelve release confirmations

These confirmations are deliberately not scored from source inspection alone. A numeric score requires reproducible runtime evidence and, for visual criteria, screenshots from the target viewport/device.

| # | Confirmation | Current evidence | Status |
|---:|---|---|---|
| 1 | Frontend production build | CI run 44241830519, frontend job success | PASS |
| 2 | Backend automated tests | CI run 44241830519, backend job success | PASS |
| 3 | Mobile layout on a real Android viewport | No device/browser capture attached to this run | NOT VERIFIED |
| 4 | Visual styling on the rendered React screen | JSX/CSS class contract was corrected; no rendered screenshot/device validation | NOT VERIFIED |
| 5 | Google sign-in end-to-end | UI/backend code exists; production OAuth credentials and live login test absent | NOT VERIFIED |
| 6 | Session restore and secure logout end-to-end | Backend tests exist; live configured PostgreSQL/browser session test absent | NOT VERIFIED |
| 7 | Real neural chat generation | Runtime requires a compatible trained checkpoint; no production checkpoint is shipped | BLOCKED |
| 8 | Conversation persistence across reloads | Current frontend message state is in-memory only | NOT IMPLEMENTED |
| 9 | Integrated coder UI and API workflow | Workspace class exists but is not exposed in the frontend/API | NOT IMPLEMENTED |
| 10 | Projects workflow | Navigation item is disabled; project persistence/UI absent | NOT IMPLEMENTED |
| 11 | Admin dashboard UI | Admin API exists; dashboard UI is absent | NOT IMPLEMENTED |
| 12 | Android package build, signing and device installation | Capacitor config exists; native `android/` project/build workflow/artifact/device test absent | NOT IMPLEMENTED |

No 8/10-or-higher scores are claimed. The twelve-confirmation gate is therefore **not passed**. APK generation remains blocked until every confirmation has its own evidence, every score is at least 8/10, and the mean is at least 8.5/10.

## Known implementation limits

- Projects and Development navigation controls are disabled.
- Coder workspace read/write capability is backend code only; no interactive coder UI or safe command-execution sandbox is available.
- Frontend messages are not persisted.
- Google OAuth credentials and PostgreSQL deployment are not configured or tested end to end.
- No production-trained multilingual model/checkpoint or capability benchmark suite is available. Previous 60-step CPU demo training (86,720 parameters, 320-token vocabulary, validation loss 4.4094242) proved the optimization path only; generated text was incoherent.
- Distributed rate limiting, monitoring, backups, incident recovery and public deployment remain incomplete.

## Release rule

Do not create, sign, or distribute an APK until all twelve confirmations above have independent runtime evidence, every score is >=8/10 and the average is >=8.5/10. Do not replace missing evidence with source inspection or a green compile.
