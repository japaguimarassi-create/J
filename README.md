# LAVOICE Forge Arena

A mobile-first 3D arena prototype inspired by the broad idea of creating weapons from natural-language instructions. This is an independent implementation and does not reuse LAVOICE code, art, models, sounds, or other proprietary assets.

## Current vertical slice

- Android-first 3D arena with touch movement, touch firing, extraction, and keyboard controls.
- Text prompt input and native Android speech-to-text input in Brazilian Portuguese.
- A deterministic assistant that normalizes Portuguese text, identifies weapon type, theme, barrel count, projectile, firing mode, target, and effect.
- Procedural 3D weapon assembly using modular meshes and materials.
- Basic projectiles and training targets with effect-specific hit feedback.
- GitHub Actions workflow that runs parser checks, builds the Android speech bridge, exports an arm64 debug APK, validates the APK, and uploads it as an artifact.

## Example prompt

`Crie uma pistola de gelo com dois canos que dispara rajadas e congela os inimigos`

The assistant extracts the action, object, type, theme, component count, projectile behavior, and target. The weapon factory then assembles the visible model and its firing configuration.

## Speech input

On Android, the **VOZ** control launches the system speech recognizer with the `pt-BR` language preference. Availability and offline recognition depend on the speech services and language packs installed on the device. Text input remains available as a complete alternative.

## Build

The workflow is `.github/workflows/android-apk.yml`. It uses Godot 4.7.2 stable, Java 17, the Android SDK, and the Godot Gradle export template. The APK is published as the GitHub Actions artifact `LAVOICE-ForgeArena-Android-APK`.

## Scope

This is the first playable foundation, not a finished clone of LAVOICE. It deliberately starts with a small, testable creation system. More weapon parts, projectile families, extraction blocks, bots, destructible terrain, and multiplayer can be layered on without replacing the parser or weapon factory.
