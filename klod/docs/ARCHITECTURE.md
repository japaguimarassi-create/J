# Klod architecture and identity

## One AI, one agent, one coder capability

Klod has one user-facing AI identity, one neural runtime and one continuous conversation/task state. The cognitive goals draw on the public capabilities associated with Claude Fable 5.2 and Claude Opus 5.5. Claude Code is the reference for the integrated coding workflow. These are design targets, not imported models, proprietary weights, prompts or private implementations.

There are no separately simulated specialist agents and no coordinator that pretends to delegate to model instances. The coder is a built-in capability of the same Klod agent: authorized workspace reads/writes, with later extensions for diffs, Git and an isolated command runner. A single model may call approved tools once a real tool-use protocol has been trained and verified. Until that exists, tools are exposed as explicit backend capabilities rather than fabricated autonomous actions.

The phrase "maximum capability" is a long-term engineering target, not a measured property of the current experimental model. Klod's model must earn capability through licensed data, training, evaluations and hardware.

## Neural model

One decoder-only autoregressive Transformer; learned token embeddings tied to the output projection; pre-normalization with RMSNorm; causal multi-head self-attention; rotary positional embeddings (RoPE); GELU feed-forward layers; residual connections; next-token cross-entropy. Parameter count is computed from instantiated trainable weights.

## Tokenizer

Versioned byte-level BPE. The 256 initial byte IDs represent valid UTF-8 data. Four reserved special IDs are fixed at tokenizer creation, and learned merge IDs are appended. A format-v2 loader preserves the old token and special-token IDs when migrating existing tokenizers. The format-v3 serializer records token bytes, merge rules, merge frequencies, special-token IDs and the runtime Unicode database version.

No normalization is performed, so decode(encode(text)) preserves the exact string for valid UTF-8 text. BPE can represent all valid Unicode scalar values without having seen them during training. It cannot create understanding of an unseen language or script by itself.

## Independent versioning

- Software version: Git commit/branch and deployment release.
- Tokenizer version: serialization format, vocabulary size and ordered merge table.
- Neural model version: model configuration, parameter count, checkpoint lineage and training step.
- Dataset version: immutable manifest, license/permission record and preprocessing hash.

A software update must not silently rewrite the tokenizer or model weights. Tokenizer growth appends IDs; model expansion copies compatible weights and adds capacity; code changes are versioned in Git. Candidate versions are trained and evaluated separately. The previous stable checkpoint remains available until the candidate passes evaluation.

## Safe model expansion

The current expansion path preserves model width and attention-head count. It may append vocabulary items, increase context length, add Transformer blocks and widen feed-forward layers. Existing attention and overlapping weights are copied. New feed-forward columns and new residual branches are initialized so the old network's output on its old vocabulary is initially preserved. New vocabulary embedding rows start at zero and learn through continued training.

Changing the embedding width or number of attention heads changes internal tensor geometry and is deliberately rejected by the current expansion utility. Such changes require a separately versioned architecture migration, not tensor truncation or blind copying.

## Training

The trainer performs actual autograd/backpropagation and AdamW optimization with gradient clipping, warmup/cosine scheduling, chronological train/validation split, atomic checkpoints and exact resume support. Model expansion records its parent checkpoint and begins with a fresh optimizer state because parameter shapes changed. The parent file is never replaced.

Only authorized corpora may be used. A small run proves that optimization executes; it does not demonstrate language competence.

## Identity and deployment boundaries

React + TypeScript + Vite is the web/mobile client. FastAPI exposes model, identity and session services. Training and inference requiring accelerators belong in an appropriate worker, not Vercel serverless functions. PostgreSQL, production identity and a fully isolated coder execution service require their own deployment configuration and operational tests.

## Android

Capacitor 8 is configured as the planned wrapper. No APK build is run before the twelve UI gates pass with evidence.
