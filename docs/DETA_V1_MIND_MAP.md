# Deta v1.2 — mental map

## Android app
- Rebuilt native interface, no old Activity code in the active source tree
- Current menu retained under `archive/menu-v1/`
- Empty creation screen, prompt composer, local recent chats and deletion
- Robust saved-history bounds and malformed-JSON recovery

## Original AI model
- The project's original `DetaFiveGroupModel` checkpoint is packaged into the APK
- 400,000 parameters, five groups of 80,000
- Python export checks model format and hashes weights
- Java inference runs locally; no model API and no network permission
- The model receives the raw user prompt with no predefined owner-specific system/personality prompt
- Local drafts are experimental because the byte-level model is small

## App creation
- Natural-language prompt -> original model inference + structured project builder
- Game starter, social-feed starter, or utility app
- Real HTML/CSS/JS files, README and project metadata
- Preview inside the app with network disabled
- Export project ZIP via Android document picker
- Reopen local conversation and regenerate its project payload

## Build and tests
- Robolectric app-startup test
- Neural weights load/greedy continuation test
- Project ZIP feature/structure tests and input escaping checks
- Clean Gradle build, model payload SHA, package identity, zipalign and signature checks
- Debug APK uploaded by GitHub Actions
