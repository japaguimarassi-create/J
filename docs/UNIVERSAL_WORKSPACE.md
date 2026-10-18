# Kowork universal workspace: browser and operating-system access

## Browser access

The Android app now includes `app/src/main/java/ai/kowork/mobile/KoworkBrowserScreen.kt`, a desktop-mode WebView with JavaScript, navigation, document-picker upload, downloads, cookie/cache controls and an explicit page-to-chat context action. It asks for user and Android permission before giving a site access to camera, microphone or location. The user can start searches from chat and return visible page text to the local model. This is user-driven browsing, not autonomous browser control. The separate `ai/tools/browser.py` source is a Playwright Chromium prototype for a Linux workspace.

Install it in a Linux development workspace:

```sh
python -m pip install playwright
python -m playwright install chromium
python -m ai.tools.browser --url https://create.roblox.com/docs/ --screenshot artifacts/roblox-docs.png
```

This prototype is a standalone local tool. It is not connected to the Android UI or local model. The chat's direct web research path finds up to four public links, safely tries to read the top result (HTTPS only, public DNS target, bounded redirects and a 512 KiB page cap), chooses an excerpt related to the user's question, then passes that excerpt and URL into the local-model prompt. A separate Web PC tab lets users browse pages and explicitly hand visible page text into chat. If direct search fails, local response generation still proceeds with a note that sources were unavailable. It requires Playwright and a browser runtime. It only navigates HTTPS, blocks localhost/private/reserved network targets, and does not bypass login, CAPTCHA, paywalls, DRM, or website access controls. Sites may still block automated browsing or require the user to sign in manually. Downloads, uploads, account changes, purchases, publishing and destructive actions must have a separate explicit user-confirmation layer before being automated.

## Broad internet access is not the same as copying the entire internet into training

- `ai/collect_knowledge.py` is the bounded collector for approved public documentation.
- `ai/knowledge_sources.json` records sources, path limits, licenses and attribution.
- `ai/knowledge_index.py` builds a local SQLite BM25 search index with source citations.
- The browser can read a public page live without automatically adding it to training data.
- When the CI collector successfully uploads `documents.jsonl`, tap **Importar base** inside Chat to import it. `KoworkKnowledgeStore.kt` validates HTTPS citation URLs, applies import size/document limits, stores license and attribution, and creates a private on-device SQLite FTS4 index. Chat queries this index before generation and displays returned source details separately. The app builds its own index from JSONL; it does not consume the Python `.sqlite3` file directly.
- Never put credentials, session cookies, private data or scraped account content into model training data.

The collector is intentionally bounded and license-aware. It cannot truthfully promise every website, every language, every game or every fact. New sources should be added with their terms/license, attribution, path scope and robots policy reviewed.

## Android, Linux, Windows and Roblox Studio

These environments are coordinated, not fused into one OS:

- **Android** hosts the full-screen Kowork app and can request Android features through normal permissions and visible user actions.
- **Linux** is the portable development workspace for terminal commands, compilers, Git and test jobs.
- **Windows** must run on a licensed Windows computer or VM. An Android APK cannot legally or technically bundle a full Windows installation as if it were a normal app.
- **Roblox Studio** is a desktop application. Kowork can browse Roblox Creator documentation and edit project files; controlling Studio itself needs an explicit, user-controlled Windows desktop/VM connector and a supported Studio installation.

For remote Windows/Linux machines, use authenticated connections, encrypted transport, isolated project folders, explicit user approval for destructive commands, and visible session status. Never give a model unrestricted access to personal files or run arbitrary generated shell commands as administrator.

## Current implementation status

| Capability | Status |
|---|---|
| In-app desktop WebView | Integrated in source; CI/device verification pending |
| Direct fetch URL checks | Public destination validation in direct research path; local browsing is allowed only via user-directed WebView |
| License-aware documentation collector | Integrated in branch; CI execution pending |
| Python source-aware BM25 index | Integrated in branch; CI execution pending; generated corpus artifact not yet verified |
| On-device document import and source-aware FTS retrieval | Integrated in source; build/device verification pending; requires importing the workflow's `documents.jsonl` |
| Android chat can use live web search context | Integrated in source; compile and device verification pending |
| User-controlled page-to-chat handoff | Integrated in source; CI/device verification pending |
| Model can autonomously control arbitrary browser sessions | Not integrated |
| Floating HUD | Removed from manifest and source |
| Project editor and safe terminal | Integrated in source; editor supports local files and a Termux/PRoot setup flow; CI/device verification pending |
| Remote Windows and Roblox Studio | User-provided remote desktop URL supported; no Windows VM or native Studio bundled |
| APK build and device validation | Attempted with GitHub Actions, but jobs failed before steps/logs; compilation remains unverified |

Do not report a capability as working until it has been integrated and tested end to end.
