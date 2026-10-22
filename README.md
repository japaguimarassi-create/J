# Deta AI — Android local model and app creator

Deta is a mobile-first app creator that runs the original Deta neural checkpoint directly on Android, without a hosted AI API. The Android package includes a local inference runtime plus a structured project builder for playable browser games, social-feed prototypes, and utility apps.

The application is reconstructed natively. The former interface is retained under `archive/menu-v1/`; it is not compiled into the app.

## Android app

- **Original neural model:** `DetaFiveGroupModel`, 400,000 trained parameters, five 80,000-parameter groups.
- **Offline inference:** model weights are exported from the verified training checkpoint to a 1.6 MB little-endian float32 asset, then loaded by a Java GRU runtime inside Android.
- **Project creation:** a user's raw request is processed by the trained local model for an experimental neural draft and passed to a structured generator which makes runnable starter files.
- **Projects supported:** browser game, social feed, and utility/checklist app.
- **Preview and export:** projects can be previewed inside the app and saved as a ZIP through Android's document picker.
- **History:** chats are stored locally, can be searched from the drawer, and can be deleted.
- **No AI API:** the app has no Internet permission and contains no OpenAI/Gemini API calls.
- **Custom rules:** there is no pre-filled personality prompt or owner-specific internal rules. The user prompt is sent directly to the local model.

## Quality and limitation

The 400k model is real and comes from the project's existing trained checkpoint. It is a compact byte-level model trained on a small approved code corpus, not a modern general-purpose LLM. Its drafts can be incoherent. The app therefore combines neural inference with tested structured project templates and labels that distinction rather than claiming arbitrary code generation is solved.

Generated projects are local prototypes. A single HTML/JavaScript ZIP is not the same as a compiled native APK, multiplayer backend, secure account system or production release. Those capabilities require separate implementation and testing.

## Build and validation

The Android workflow:
1. Downloads the previously trained `deta-400k-five-group-checkpoints` artifact only if the exported model asset is not already present.
2. Validates the checkpoint type, all five groups, 400,000 parameter count, tensor shapes, finite numeric values and SHA-256 digest.
3. Exports the original weights to a little-endian asset, then stores that asset in the repository for reproducible future builds.
4. Runs Robolectric app-startup tests, local model inference tests, and project-builder tests.
5. Builds a clean debug APK and checks package identity, archive integrity, alignment, signature and presence of the model weights.
6. Publishes the installable APK as a GitHub Actions artifact.

Current Android package: `app.deta.mobile.debug`. Version: 1.2.0-debug (`versionCode 120`).

See `docs/DETA_REBUILD_MINDMAP.md` for the complete project map and `docs/ARCHITECTURE.md` for the model/export implementation.

## Core Python project

The `deta/` package remains available for checkpoint training, public web research, local knowledge retrieval, project generation and four-pass code verification. These tools are separate from the native Android model runtime; the mobile build does not call the Python CLI or a remote service.
