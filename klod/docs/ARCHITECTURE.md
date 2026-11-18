# Architecture

The React client is the mobile-first interface. FastAPI owns authentication, sessions, persistence, authorization, agent coordination and audit events. Training and inference require dedicated worker infrastructure; they do not run in Vercel serverless functions.

The neural foundation is a causal decoder-only Transformer with embeddings, rotary positional embeddings, multi-head causal attention, pre-normalization, residual paths, SwiGLU feed-forward layers and next-token cross-entropy. Parameter counts are measured from the instantiated model.

The tokenizer is byte-level BPE. Every UTF-8 byte is representable, allowing lossless round trips for arbitrary valid UTF-8 input. Merge rules are learned from operator-supplied corpora and serialized with a format version.

Agents must be real modules with typed inputs and outputs. A coordinator enforces deadlines, step budgets, allow-listed tools, permission checks and approval for destructive or external operations. Shell execution is disabled by default.

Google identity must be verified server-side. The stable Google sub claim is the external identity key; an email suffix is not proof of authentication. First-admin initialization must be atomic in the database.

Vercel serves the static web application. A separate long-running service hosts FastAPI, PostgreSQL connectivity, inference and training. Capacitor packaging is postponed until mobile release gates pass.
