# KLOD — development and release ledger
Date: 2026-11-18

## Current state

Klod remains isolated under `klod/` on branch `klod-development`; other repository projects are preserved. The implementation is an experimental platform, not a production-trained general assistant.

The architecture remains **one Klod AI, one agent and one neural runtime**. Coder is an integrated capability of that same agent. There are no simulated specialist agents.

Latest release-evidence ledger: `docs/release-evidence.json`.
Latest fully green CI evidence: https://github.com/japaguimarassi-create/J/actions/runs/44364778024
Browser screenshots and Playwright report artifact: https://github.com/japaguimarassi-create/J/actions/runs/44364778024/artifacts/14456358220

## Implemented and tested

- UTF-8 byte-level BPE tokenizer with append-only expansion, exact round-trip reconstruction, merge metadata and Unicode coverage tests.
- Decoder-only Transformer with RoPE, causal multi-head attention, RMSNorm, residual blocks, GELU feed-forward layers and tied embeddings.
- AdamW training, train/validation split, gradient clipping, warmup/cosine scheduler, atomic checkpoints, exact resume and safe model expansion.
- One `KlodAgent` with a project-scoped, per-user Coder workspace. Read/list/write use path confinement, byte limits, exact-path approval and atomic writes. Host shell execution is deliberately absent.
- FastAPI authentication, chat, persistent conversations, projects, file workspace and admin endpoints.
- PostgreSQL migrations for identity/sessions, conversations/messages and projects.
- First-admin transaction and per-session CSRF validation; HttpOnly session cookies.
- React/TypeScript mobile-first UI with conversation history, project creation, file editor/Coder and admin dashboard.
- PWA setup and Capacitor 8 configuration.
- CI now runs backend tests against PostgreSQL 16, frontend production build, and Playwright browser acceptance tests for mobile, desktop and authenticated workflows.
- The PostgreSQL integration test covers identity/session lifecycle, first-admin role, HttpOnly cookie, CSRF, logout, non-admin rejection, chat persistence, project ownership, file read/write and admin counts.
- The browser suite completed **9/9** tests: mobile layout/overflow/style, mobile menu, prompt suggestion, desktop layout, conversation restore, project+Coder save, admin view, chat send and conversation restoration after reload.
- Latest green commit run reported **46 backend tests passed** and **9 browser tests passed**. The browser artifact contains a rendered mobile screenshot and Playwright report.

## Twelve acceptance confirmations

Scores are recorded only where there is reproducible evidence. The viewport checks use Chromium's Pixel 7 mobile emulation at 390×844; they do not claim a physical Moto G04S test.

| # | Confirmation | Score | Status | Evidence / limitation |
|---:|---|---:|---|---|
| 1 | Frontend production build | 9.2/10 | PASS | CI 44364778024 |
| 2 | Backend tests with PostgreSQL 16 | 9.1/10 | PASS | CI 44364778024; 36 tests passed |
| 3 | Mobile layout at emulated Pixel 7 viewport | 8.6/10 | PASS | CI 44364778024; mobile screenshot and no horizontal overflow |
| 4 | Rendered visual styling and CSS checks | 8.8/10 | PASS | CI 44364778024; screenshot plus computed style assertions |
| 5 | Live Google OAuth with real client credentials and externally issued token | — | BLOCKED | Automated verifier/session tests use a controlled verifier; no production OAuth client ID or live external login has been configured |
| 6 | PostgreSQL session, HttpOnly cookie, CSRF and logout | 8.7/10 | PASS | CI 44364778024; TestClient against real PostgreSQL |
| 7 | Production-quality neural checkpoint and real product inference | — | BLOCKED | A 2-step CPU training/inference smoke test exists, but the generated text was incoherent; no production checkpoint or capability benchmark exists |
| 8 | Persistent conversations and restore after reload | 8.7/10 | PASS | CI 44364778024; PostgreSQL chat persistence plus browser reload workflow |
| 9 | Integrated Coder workspace, isolation, read and write | 8.8/10 | PASS | CI 44364778024; unit, PostgreSQL API and browser workflow tests |
| 10 | Project creation and listing | 8.8/10 | PASS | CI 44364778024; PostgreSQL API and browser workflow tests |
| 11 | Admin panel and server-side permissions | 8.8/10 | PASS | CI 44364778024; admin browser view, admin API and non-admin 403 test |
| 12 | APK build, install and launch on Android emulator/device | — | PENDING | No APK artifact has been generated; candidate workflow is intentionally gated behind confirmations 1–11 |

**Current count: 9 PASS, 2 BLOCKED, 1 PENDING.** The release requirement is not met. Scores are not assigned to blocked or pending items, and no mean is claimed.

## Training and model-quality qualification

The existing CPU smoke tests train a small checkpoint and run neural inference. Historical demo evidence used 86,720 parameters, vocabulary size 320, 60 optimizer updates and validation loss 4.4094242; generated text was incoherent. Current unit tests also train a tiny model and verify checkpoint loading/inference. These prove the training mechanics, not useful language capability. A licensed, sufficiently large corpus, continued training, evaluations for language/reasoning/math/coding and model-quality thresholds are still required.

## Android release protection

The GitHub Actions workflow contains an opt-in Android candidate job. It is skipped on ordinary pushes. Manual execution requires backend, frontend and browser jobs to pass and runs:

`python klod/scripts/release_gate.py --through 11`

Only then does it generate a Capacitor Android project, build a debug APK, install/launch it in an Android emulator and upload APK/screenshot evidence. The evidence ledger must still include all twelve confirmations, each >=8/10 and average >=8.5/10, before final release. A debug candidate is not a production-signed APK.

The release checker uses fixed thresholds, rejects non-finite/out-of-range scores and requires evidence links to this repository's GitHub records. Its test suite checks valid records, missing evidence, invalid scores, external links and the average threshold.

## Remaining blockers

1. Configure a real Google OAuth web client, exact allowed origins and production secrets; test an actual externally issued ID token through the deployed browser/API.
2. Train and validate a genuinely useful Klod checkpoint on authorized data, package a compatible checkpoint and run product-level chat inference.
3. Provision a production PostgreSQL instance, HTTPS deployment, monitoring, distributed rate limits, backups and recovery.
4. Execute the guarded Android candidate workflow after gates 1–11 pass, inspect emulator evidence, and separately validate installation on the target phone.
5. Add a production signing configuration only after the candidate passes acceptance.

The coder intentionally remains a guarded file workspace/editor. Shell execution, Git operations and a fully isolated command runner are not represented as completed functionality.
