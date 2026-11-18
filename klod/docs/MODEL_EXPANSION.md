# Neural model versioning and expansion

## Independent version

Every checkpoint stores:
- Full ModelConfig.
- Model state dictionary.
- Parameter count measured from the live model.
- Training step and validation loss.
- Tokenizer vocabulary size and tokenizer format version.
- Parent checkpoint reference when expanded.
- Expansion report when applicable.

The software repository commit and the dataset manifest should be recorded alongside release artifacts. A code update alone does not imply that the model was retrained.

## Supported capacity growth

The current safe expansion utility can:
- increase tokenizer vocabulary size;
- increase the context window;
- append Transformer blocks;
- widen the feed-forward layers in existing blocks.

It deliberately preserves d_model and n_heads. Those dimensions define attention-head geometry and RoPE layout. A future width/head migration must be implemented and evaluated as a new architecture version.

## Function-preserving initialization

The utility copies all old weights. When feed-forward width increases, the new down-projection columns are zero-initialized so added channels do not alter the old model output before training. Newly appended Transformer blocks have zeroed attention output projections and feed-forward down projections, so each new residual block starts as an identity mapping. New vocabulary embedding rows start at zero.

A unit test compares old-token logits before and immediately after expansion. That check does not prove the expanded model has learned anything; only continued optimization and evaluation can establish improvement.

## Commands

Resume exactly the same shapes and tokenizer:

    python -m klod.training.train --dataset data/continued.jsonl --output-dir artifacts/resumed --tokenizer artifacts/v1/tokenizer.json --resume artifacts/v1/checkpoints/latest.pt --steps 30000

Expand from a prior checkpoint while growing vocabulary, depth and feed-forward capacity:

    python -m klod.training.train --dataset data/new-corpus.jsonl --output-dir artifacts/v2 --tokenizer artifacts/v1/tokenizer.json --expand-tokenizer --expand-from artifacts/v1/checkpoints/latest.pt --vocab-size 65536 --seq-len 256 --n-layers 6 --d-ff 1536 --steps 50000

--steps is the target cumulative optimizer step stored in the checkpoint. The expanded model starts a fresh AdamW state because the parameter shapes changed; the source checkpoint is never overwritten. The training log reports the actual vocabulary size and parameter count.

## Stable promotion policy

A candidate must pass tokenizer/model tests and task evaluations before it can be designated stable. A lower-scoring candidate must not replace the stable checkpoint. Preserve parent checkpoints and evaluation reports for rollback.
