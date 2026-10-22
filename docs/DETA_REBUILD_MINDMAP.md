# Deta AI — reconstruction and integration map

## Product goal
- Mobile-first IA que cria projetos de apps e jogos
- Reuse the actual Deta checkpoint previously trained in this repository
- No hosted AI API and no Internet permission in the Android APK
- User-defined behavior remains unconfigured; no hidden personality prompt is injected

## Android shell
- Native Java Activity rebuilt independently
- Minimal dark interface with Deta identity
- Recent conversations and local persistence
- Search and delete from the menu drawer
- New creation flow and prompt composer
- Recovery screen for startup errors
- Accessible labels and bounded saved history

## Original Deta model
- Source: `deta-400k-five-group-checkpoints` artifact from training run 39690950684
- Architecture: `DetaFiveGroupModel`
- 400,000 trainable parameters total
- Five additive byte-level GRU groups of 80,000 parameters
- 30,000 cumulative training updates in the source checkpoint
- 343 records in the source manifest
- Python exporter validates tensor names, exact shapes, finite weights, group count and parameter total
- Export format: ordered little-endian float32 binary, 1,600,000 bytes
- Android runtime reimplements GRU reset/update/new gates, hidden affine transform, output projection, group summation, and top-k sampling
- Startup does not load the model; weights are loaded lazily on the first creation request

## App/project creation path
1. Accept the user's raw prompt without a pre-filled system/personality prompt.
2. Run the original trained neural model locally to produce a byte-level experimental draft.
3. Classify the request into game, social-feed, or utility prototype.
4. Generate actual HTML, CSS, JavaScript, README, and project metadata files.
5. Offer embedded preview with network loads blocked.
6. Export a ZIP through Android's document picker.
7. Store the conversation locally, including enough project metadata to regenerate the ZIP later.

## Projects
- Game: 30-second touch-based target game, score, restart and local record
- Social: local posts, search, likes, comments, delete and browser storage
- Utility: local checklist, add, complete, delete and clear completed
- Output is a working starter project; arbitrary native APK compilation is not included in the mobile app yet

## No-network and privacy posture
- No `android.permission.INTERNET`
- No OpenAI/Gemini API or other hosted AI call
- WebView preview blocks network loading and only inlines the generated local HTML/CSS/JS
- Neural inference runs on the device
- Conversations are stored in local Android preferences with size limits
- Export destination is chosen by the user through Android's document picker

## Tests
- Robolectric app startup and composer visibility
- The original 400k weights load and produce a known greedy continuation for a fixed prompt
- Project archive contents and ZIP structure
- Game, social, and utility feature assertions
- HTML injection escaping in user-supplied prompt text
- Model checksum, exact weight size, source checkpoint metadata and 400k parameter count
- Clean Gradle assemble, zipalign, apksigner, package/version identity and ZIP integrity

## Limitations to be explicit about
- The neural checkpoint is small and byte-level; completions can be incoherent or invalid.
- The structured generator is what makes the three starter project types runnable.
- Generated prototypes require review and testing before publishing.
- The current mobile build creates browser-based project ZIPs; it does not yet compile arbitrary Android-native projects to APK.
- Robolectric validates Activity startup in a JVM Android environment, not every physical handset. A physical-device test remains valuable.

## Archive
- `archive/menu-v1/`: original previous menu and related Android files retained as historical reference.
- Current app source under `app/src/main/` is independent of that archive.
