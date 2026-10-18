# Kowork training design

## Session mesh model

The planner treats each causal-language-model sequence window as one session ID. Given 100 logical queues and 400,000,000 sessions per queue, the target is 40,000,000,000 sessions. Session ID i is assigned to queue i modulo 100, balancing each complete round of 100. A cursor determines per-queue counts by quotient/remainder; no per-session job object is retained. Worker ranks receive disjoint IDs within an optimizer step based on rank, microstep, batch size, and accumulation count.

Queue sharding is a scheduling abstraction. It does not create compute capacity by itself. GPU parallelism comes from the actual distributed worker group. The trainer reports the full target and current bounded-run budget so smoke tests cannot be confused with the full plan.

## Efficiency features

- Grouped-query attention reduces key/value projection size relative to full multi-head KV attention.
- FSDP full-shards parameters, gradients, and optimizer states across actual distributed ranks.
- Meta-device construction avoids materializing the entire 10B model on every process before sharding.
- BF16 mixed precision, activation checkpointing, gradient accumulation, gradient clipping and warmup/cosine learning-rate scheduling target throughput and stability.
- Training windows are sampled inside their assigned mesh's corpus region when the region is large enough.
- Atomic checkpoints avoid leaving a partially overwritten weight file after interruption.
- A held-out file split provides validation-loss tracking; exact duplicate content is removed before the split.
- JSONL metrics include loss, validation loss, session progress, per-mesh counts, learning rate, elapsed time, and checkpoint location.

## Data safety and quality

The local preparer excludes common generated/dependency directories, skips obvious credential files, redacts several common credential patterns, deduplicates exact normalized file content, and creates a held-out split before fitting the tokenizer. These filters are best-effort, not a security guarantee. Inspect emitted training and validation corpora, verify licenses and remove confidential data before long training.

Near-duplicate removal, domain balancing, benchmark contamination checks, broad coding/general-knowledge evaluations and safety evaluations remain future work. Corpus size alone is not a quality measure.

## Model and token budget

The 10B architecture count is validated from configuration, not a trained checkpoint. At 40 billion sequence sessions and context length 2,048, the target represents 81.92 trillion token positions. This is a massive compute job and does not mean 40 billion unique conversational evaluations have happened. The user-specified session target is recorded explicitly rather than claimed as completed.

## Evidence levels

1. Architecture validation: exact configured parameter count.
2. Unit tests: session assignment, budget accounting, model forward/backward, generation, and data filtering.
3. CPU smoke run: actual gradient updates on a small model, held-out validation, checkpoint save/load, and generated sample.
4. Full pretraining: pending adequate hardware, a large lawful corpus, logs and a 10B checkpoint.

## Research references

- Hoffmann et al., Training Compute-Optimal Large Language Models: https://arxiv.org/abs/2203.15556
- PyTorch FSDP: https://docs.pytorch.org/docs/stable/fsdp.html
- NVIDIA Megatron-LM parallelism: https://github.com/NVIDIA/Megatron-LM/blob/main/docs/user-guide/parallelism-guide.md
- Deduplicating Training Data Makes Language Models Better: https://research.google/pubs/deduplicating-training-data-makes-language-models-better/
- A Pretrainer's Guide to Training Data: https://aclanthology.org/2024.naacl-long.179/
- Scaling Laws Revisited: Modeling the Role of Data Quality: https://openreview.net/pdf?id=x54wwB6QvL
