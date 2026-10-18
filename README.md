# Kowork AI

This branch contains a native Android app and an experimental offline inference runtime for the original Kowork decoder-only Transformer. The app does not call an external AI API.

## Android app

Requires JDK 17, Gradle 8.10.2 and Android SDK Platform 35:

```bash
gradle --no-daemon assembleDebug
gradle --no-daemon testDebugUnitTest
```

GitHub Actions is configured to build a debug APK and publish it as the `kowork-android-debug` artifact. See [Android validation](https://github.com/japaguimarassi-create/Z-do-Black-/actions/workflows/android-apk.yml?query=branch%3Akowork-android-app).

## Using the local model

1. Install the app APK.
2. Download the exported `Kowork-Android-Model.kwm` file separately.
3. Open Chat and select **Importar modelo local**.
4. Pick the `.kwm` file in Android's document picker.
5. Send a prompt. Generation runs locally on the device after import and does not use network access or API keys.

The model file is stored in the app's private files directory. The import path validates the file header, architecture, tensor shapes and payload before it is accepted. Re-importing the model replaces the locally installed model.

## Actual model limits

The included weights are from the experiment's best historical checkpoint at step 6,100, not the worse final checkpoint. This is an experimental model with **623,232 parameters**, a 512-token vocabulary and a 128-token context. It is not the 10,046,763,008-parameter architecture and is not a general-purpose conversational model. The small training corpus produced poor free-form generations, so output can be incoherent. Connecting real inference is not evidence of high quality.

A separate continuation was rerun from cycle 13,650 to 53,650 with the monotonic validation guard active from the first block. It accepted 40,000 additional optimizer updates across 400 blocks; 11 regressing candidates were rolled back and retried. An audit of the accepted history found zero blocks whose validation loss exceeded the preceding accepted value by more than the numerical tolerance of 1e-6. Validation moved from 3.0302247 at the first accepted block to 3.0279833 at the end of the guarded run. The historical best rolling validation loss remains 2.9630988 around cycle 6,100, so inference exports that best checkpoint instead of the later, worse checkpoint.

The 100 logical training queues documented in the core are a plan, not 100 physical training clusters. The 10B configuration is an architecture count only; no full 10B checkpoint has been trained.

## Other app features

- Native Compose UI for chat, restricted diagnostic terminal, training information and saved preferences.
- Native full-screen assistant interface with Chat, Research, Terminal, Training, and Settings tabs; no floating overlay service.
- No hard-coded API key, fake login, arbitrary shell execution, or silent file access.
- No in-app training worker yet. The training panel reports checkpoint data only.
- The Android Actions workflow has not yet produced a validated APK: recent runs fail before executing any steps and provide no usable job logs.
- No release signing or Play Store distribution configured.

## Internet and universal workspace prototype

- The Android manifest now declares the standard Internet permission; this does not itself give the model browsing capability.
- The floating HUD service and overlay permission have been removed. The app uses normal in-app navigation.
- `KoworkWebResearch.kt` performs public web searches through DuckDuckGo HTML. When web research is enabled for a chat message, Kowork lists up to four public results, attempts to read the first result's HTTPS page with strict size/redirect limits and public-address checks, selects a query-relevant excerpt, and passes that excerpt plus its source URL as context to the imported local model. Results and URLs are shown separately. The search query is sent to the public search provider. This does not bypass logins, CAPTCHA, paywalls, DRM or other access controls.
- `KoworkBrowserScreen.kt` provides an in-app desktop-mode WebView with JavaScript, navigation, site-data controls, document-picker uploads, downloads and an explicit page-to-chat handoff. Site camera/microphone/location are denied unless a site asks, the user confirms, and Android grants permission. `KoworkBrowserPolicy.kt` limits navigation to HTTP/HTTPS schemes. This is a mobile WebView, not every feature of desktop Chrome.
- The direct research fetcher blocks private/local target URLs and redirects. The user-directed WebView can reach a local development server by design. Neither path bypasses logins, CAPTCHA, paywalls, DRM or site access controls.
- `ai/collect_knowledge.py`, `ai/knowledge_sources.json` and `ai/knowledge_index.py` now live on this branch. They collect a bounded set of public documentation when allowed by robots and source license metadata, and build a local SQLite BM25 index that preserves citations. The GitHub Actions job uploads the corpus and index as an artifact; the app does not bundle the Python-generated SQLite file; instead it imports `documents.jsonl` and builds a device-local SQLite FTS4 index that the chat can query.
- The collection workflow can run manually and weekly after it is merged to the repository's default branch. It is research/retrieval, not a weight-training job. When `documents.jsonl` is available from the workflow artifact, tap **Importar base** in Chat and select that file: Kowork stores a bounded, citation-preserving local FTS index and retrieves relevant snippets for subsequent chat prompts. The corpus has not been generated yet because current GitHub Actions runs fail before any steps execute.
- `KoworkWorkspaceScreen.kt` includes local project/file editing for Luau, Python, JavaScript, HTML and Kotlin, safe diagnostics, import/export, Termux/PRoot setup, and a user-configured remote Windows URL. This coordinates separate environments; it does not bundle Windows or run native Roblox Studio on Android.
- `assets/kowork-icon.svg` is the editable vector source for the Kowork icon.
- Setup and boundaries: [Universal workspace documentation](docs/UNIVERSAL_WORKSPACE.md).
- Browser safety tests: [GitHub Actions workflow](https://github.com/japaguimarassi-create/Z-do-Black-/actions/workflows/browser-safety.yml?query=branch%3Akowork-universal-workspace).
- Public knowledge pipeline: [GitHub Actions workflow](https://github.com/japaguimarassi-create/Z-do-Black-/actions/workflows/knowledge-collection.yml?query=branch%3Akowork-universal-workspace).

Windows and Roblox Studio still require a licensed Windows host or VM with Studio installed. They cannot be merged into a normal Android APK by adding permissions. The cross-platform design coordinates separate environments; it is not a single combined operating system.
