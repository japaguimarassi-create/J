# Kowork Android app

Native Compose UI plus experimental offline inference using the original Kowork checkpoint. No external AI API is used.

## Build

Requires JDK 17 and Android SDK Platform 35.

```bash
gradle --no-daemon assembleDebug
gradle --no-daemon testDebugUnitTest
```

GitHub Actions is configured to upload the debug APK as the `kowork-android-debug` artifact when its build and test steps pass.

## Install and import the model

- Install the generated debug APK.
- Download the separately provided `Kowork-Android-Model.kwm` artifact.
- In Chat, tap **Importar modelo local** and select the file through Android's document picker.
- After validation, prompts are generated on-device using the imported checkpoint.
- The model is kept in the app's private internal files. The app has no Internet permission and does not call an AI API.

The importer validates the file magic, architecture dimensions, complete set of 21 tensors, tensor element counts and trailing data. If import fails, the previous model remains until it has been validated. Model replacement is local.

## Limitations that matter

- The shipped weights are checkpoint 6,100 of a 623,232-parameter comparison model with a 512-token vocabulary and 128-token context.
- They are not trained 10B weights and do not demonstrate general reasoning ability. The current corpus is tiny and free-form generation can be incoherent.
- The strict training rerun reached global cycle 53,650: 40,000 additional optimizer updates from cycle 13,650.
- The monotonic validation guard was active across all 400 accepted blocks; 11 regressing candidates were rejected and rolled back. An audit found zero validation regressions larger than the 1e-6 numerical tolerance.
- Validation loss moved from 3.0302247 at the first accepted block to 3.0279833 at the end of the guarded run.
- The historical best checkpoint remains around cycle 6,100 (rolling validation loss 2.9630988), so this is the checkpoint exported for app inference rather than the worse final checkpoint.
- GitHub Actions currently fails before any job step runs and exposes no usable log, so the Android APK remains unvalidated.
- The training panel is informational; there is no on-device training worker.
- The terminal accepts only explicit diagnostic commands; it does not run arbitrary shell code.
- HUD overlay requires the user to grant Android's system permission.
- No real OAuth provider, release signing, or Play Store publication is configured.
