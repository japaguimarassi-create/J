# Deta Android — rebuilt local base

This branch now contains a clean rebuild of the Android application's interface. It is intentionally **not an AI app yet**: the current Android package contains no model, prompt engine, web search, network permission, AI API, or automatic assistant response. The owner can define the future AI behaviour separately.

## Features in the rebuilt base

- Fresh native Android activity and minimal Deta identity
- Local conversations and user-written messages
- Conversation creation, recent-history drawer, title filtering, delete current chat, and long-press deletion
- Local persistence with bounded history
- Recovery from malformed local JSON
- No internet permission and no runtime dependencies beyond the Android platform

Messages are saved locally; this build does not fabricate assistant responses.

## Previous menu retained

The earlier implementation is preserved in `archive/menu-v1/`. These files are historical references only and are not compiled into the Android app.

## Mind map

See `docs/DETA_REBUILD_MINDMAP.md` for the complete map of the new application's scope and validation plan.

## Build and verification

The GitHub Actions workflow runs JVM unit tests, performs a clean Android build, installs and launches the app in an emulator, tests message saving and menu navigation, verifies package identity/alignment/signature, then uploads the debug APK.

Package: `app.deta.mobile.debug`
Version: 1.1.0-debug (versionCode 110)

A debug APK signed on a fresh CI runner may not update an app signed by a different debug key. If Android refuses to install it over a previous build, uninstall the previous debug package first and install the new one.
