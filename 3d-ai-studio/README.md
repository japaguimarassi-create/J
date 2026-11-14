# 3D AI Studio — Alpha 0.1

Mobile-first 3D editor and procedural neural laboratory. The Android application is generated from the web app by Capacitor and built by GitHub Actions.

## Current working scope

- Real Three.js viewport with orbit camera, selection, primitive geometry, transforms, material colors and continuous preview.
- Local scene planner that creates editable geometry from a short prompt.
- Project JSON import/export, PNG preview export and binary GLB scene export.
- Unicode byte tokenizer with stable glyph identifiers and round-trip decoding.
- Language profiles for Portuguese, English, Spanish, Mandarin Chinese, Hindi and Arabic.
- Script-aware handling for Latin, Han, Devanagari and Arabic text, including RTL metadata and grapheme segmentation.
- Seeded procedural parameter bank, sparse active inference path and a trainable output projection.
- Unit tests and Android debug APK workflow.

## Important model limits

The Atlas preset describes approximately 340 million virtual procedural parameters. They are generated deterministically by index rather than stored as a 340-million-weight checkpoint. The on-device forward path evaluates a reduced active width to limit mobile CPU and memory use. Only the output projection is trainable in this alpha. The network begins without pretrained linguistic knowledge; training it on a short text does not make it a general-purpose language model. The scene planner is rule-based and does not claim to be text-to-3D diffusion.

## Six language profiles

The current profiles are Portuguese, English, Spanish, Mandarin Chinese, Hindi and Arabic. Unicode code points are preserved through UTF-8 byte tokens. Han ideographs are segmented as characters, Devanagari is segmented as grapheme clusters, and Arabic is normalized without tatweel or optional harakat for analysis. This is an engineering baseline, not a complete linguistic morphology or translation system.

## Run locally

Use Node.js 22 or newer. Run npm install, npm run verify and npm run dev from this folder.

## Android build

The workflow at .github/workflows/3d-ai-studio-android.yml installs Node, Java and Android SDK, creates the Capacitor Android shell, builds the debug APK and uploads it as a workflow artifact. Open the workflow run in the repository Actions tab and download the artifact named 3d-ai-studio-debug-apk.

## Project format

The JSON project stores editable primitive objects and their transforms. GLB export contains the current 3D object group. Animation timelines, rigged character import, video rendering and trained model checkpoints are later milestones, not features claimed by this alpha.