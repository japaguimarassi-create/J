# Deta architecture 1.2

## Android runtime

The Android app packages the original `DetaFiveGroupModel` checkpoint as `assets/deta-model.bin`. `scripts/export_android_model.py` loads the existing PyTorch checkpoint, requires five complete groups and exactly 400,000 parameters, validates each tensor shape and finite values, and writes the weights in a fixed little-endian float32 layout. The export is 1,600,000 bytes before APK compression and includes a SHA-256 manifest.

`DetaLocalModel` reimplements the PyTorch GRU one byte at a time. Each of the five groups stores its embedding, input/recurrent projections and biases, hidden scale/bias and output projection. The runtime uses the original reset/update/new gate ordering, carries hidden state forward during generation, sums all active-group logits and samples the next byte by top-k and temperature. It runs on a background executor, loads lazily, and makes no network requests.

The first launch does not deserialize the neural weights. That avoids model initialization being a cause of the Activity startup failure. The model is initialized on the first creation request and has explicit validation errors if the payload is missing, truncated or malformed.

## Project builder

`DetaProjectFactory` combines model output with a structured generator:
- Game starter: a 30-second touch-friendly score game
- Social starter: local posts, search, likes, comments and deletion
- Utility starter: local checklist with completion and deletion

The builder produces actual `index.html`, `style.css`, `app.js`, `README.md` and `project.json` files, packaged as a ZIP. Project previews inline the generated HTML/CSS/JS into a WebView with network loads and file/content access disabled. The ZIP is saved using the Android document picker.

The neural model generates an experimental draft for the request; its output is not silently treated as production-ready source. The builder is responsible for producing valid starter code and records the original prompt in project metadata. Arbitrary native APK compilation is not part of the mobile app yet.

## Conversation persistence

Conversation history remains in private Android `SharedPreferences` JSON. IDs, titles, timestamps and messages are stored with bounds on conversation count, message count and total serialized size. Assistant creation messages keep the original project prompt so the ZIP can be reconstructed when the history is reopened.

## Test architecture

Robolectric starts `MainActivity` and asserts that the composer and creation welcome view are present. The model unit test reads the binary asset, validates the 400k parameter count, and compares a fixed greedy completion against the known output from the source checkpoint. The project builder tests ZIP contents, project-type features and escaping of user-provided markup.

GitHub Actions exports the checkpoint only when the weight asset is missing, stores validated model weights in the repository for repeatable future builds, runs the JVM Android tests, performs a clean Gradle build, and verifies APK signature, alignment, package identity and presence of model data.
