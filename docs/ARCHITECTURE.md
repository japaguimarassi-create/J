# Deta architecture 0.3.1

## 1. Public web research

The deta.web module performs public HTML search and page retrieval using direct HTTPS requests without a hosted generative-AI API key. It rejects non-HTTPS URLs, URL credentials, local hostnames, non-public IP addresses, and DNS results containing non-public addresses. Download sizes and timeouts are bounded. Results include titles, snippets and source URLs.

The deta.assistant module coordinates search, bounded page reads, local indexing, passage ranking and source citations. It is a retrieval assistant rather than a generative LLM. Pages that reject automation or have no extractable text are skipped; Deta does not sign in or bypass access controls.

## 2. Local knowledge index

The deta.knowledge module stores page text, title, source URL, source type and SHA-256 content digest in a local JSON database. The index is deduplicated by URL+content digest and bounded by document count, per-document size and total database size. Queries use lexical weighting and title boosts; results remain linked to their original sources. The index is not automatically copied into neural training data.

## 3. Offline project builder

The deta.projects module can generate:
- A touch-friendly browser game with timer, score, restart and a locally saved record.
- A local social feed with creation, filtering, likes, comments, deletion and browser storage.
- A Python CLI task manager with add/list/done/remove commands.

Templates are written into a staging directory then atomically moved into the requested output path. Non-empty destinations are rejected. These are functional starter projects, not full applications with remote accounts, multiplayer servers or production authentication.

## 4. Neural model and training

The default DetaFiveGroupModel has exactly 400,000 trainable parameters: five byte-language experts with 80,000 parameters each. The earlier 79,824-parameter GRU baseline remains available. Later group output heads start at zero so inactive experts initially contribute no logits.

Training proceeds group 1 through group 5. At each stage, only the current group's parameters are optimized; earlier groups do not receive gradients. Each group produces a checkpoint. Evaluation batches are sampled once from the held-out tail segment and reused across groups.

The longer workflow warm-starts the previous model and fine-tunes each group for 5,000 steps on a broader, bounded code manifest. Checkpoints store:
- Architecture/configuration and actual parameter counts
- Current dataset SHA-256 and corpus budget
- Per-group updates and validation metrics
- Parent checkpoint hash, previous step count and previous dataset hash
- Completed group number for safe restart

The 400k model is still a compact byte-prediction research baseline. Retrieval/tools provide current factual coverage; the neural checkpoint is not a modern pretrained chat model.

The deta.inference module loads a saved grouped checkpoint and samples the next UTF-8 bytes given a prompt. Generation is local and uses temperature/top-k sampling; it is explicitly experimental and may produce malformed code or incoherent text. The CLI does not route factual questions through this generator.

## 5. Source discovery and governance

The GitHub collector uses a finite list of repositories; it is not a universal crawler. It checks repository-level license metadata before requesting source files, rejects unsupported licenses, observes file-level SPDX declarations when present, filters common secret patterns/private repositories and writes per-record URLs, licenses and hashes.

Web-retrieved pages belong to the local knowledge index and are not automatically used for training. Training records still require an allowlisted license and provenance. Dataset agreements, attribution, privacy, opt-outs and removal requests must be honored.

## 6. Four-pass verification

1. Parse supported Python, JSON and TOML syntax/formats.
2. Run configured static checks for selected risky constructs and likely embedded credentials.
3. Require an explicitly executed test runner.
4. Check source URLs/licenses and token-shingle similarity against supplied references.

Pattern-based checks can miss issues and produce false positives. Passing this gate is not proof of correctness, security or legal compliance.

## 7. Android integration

The Android implementation has four execution paths:
- Public-web retrieval uses a background executor, direct HTTPS requests, safe redirect validation, HTML extraction and a local SharedPreferences source index.
- Project templates are written under the app-private files/projects directory. The Library previews them through WebView and can share the HTML source.
- DetaLocalModel loads binary model assets from the APK and checks the fixed DTA400K1 format, weight length, finite values and SHA-256 digest before inference.
- The Java inference engine implements the trained five-group GRU: byte embedding, reset/update/new gates, group hidden scale/bias, output projection and summed logits. It performs top-k/temperature sampling without sending prompts to an AI service.

The build workflow downloads the successful training artifact, validates/exports the 400k checkpoint, builds the Android app and runs instrumentation on an emulator. APK upload is blocked until Python tests, Android source compilation and the model-generation smoke test succeed. It then verifies ZIP integrity, alignment, signature and package identity.

This runtime provides experimental byte-level continuation, not general factual reasoning. Factual web retrieval remains separate and source-attributed. Local starter projects are not yet compiled into independent APKs.
