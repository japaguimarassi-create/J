# Architecture

## Initial vertical slice

This first milestone validates a real path through the system: exact tokenization, a project-owned GPT-style decoder, next-token optimization, persistent checkpoints and inference that refuses to invent output when no model is loaded.

## Neural model

Decoder-only autoregressive Transformer; learned token embeddings tied to the output projection; pre-normalization with RMSNorm; causal multi-head self-attention; rotary positional embeddings (RoPE); GELU feed-forward layers; residual connections; next-token cross-entropy. Parameter count is computed from instantiated weights.

## Tokenizer

Byte-level BPE starts with 256 byte IDs and appends learned pair merges. It preserves UTF-8 bytes exactly, so Portuguese accents, unseen Unicode, emoji, code, numbers and whitespace can be reconstructed losslessly. Normalization is intentionally not applied.

## Training

The trainer performs actual autograd/backpropagation and AdamW optimization with gradient clipping, warmup/cosine scheduling, atomic checkpoints and resume support. A small run demonstrates that optimization executes; it does not demonstrate language competence. Use only properly licensed and authorized corpora.

## Boundaries

React + TypeScript + Vite is the web/mobile client. FastAPI exposes model services. Training and inference requiring accelerators belong in an appropriate worker, not Vercel serverless functions. PostgreSQL, production identity, the tool/agent control plane and isolated execution are future milestones.

## Android

Capacitor 8 is configured as the planned wrapper. No APK build is run before the twelve UI gates pass with evidence.