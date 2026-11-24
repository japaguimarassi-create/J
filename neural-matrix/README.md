# Neural Matrix 1B × 2B

Experimental hybrid neural architecture targeting a logical capacity of 1,000,000,000 units and 2,000,000,000 addressable connections.

## Reality check

The target describes logical capacity, not a dense tensor allocated in memory. A dense 1B × 2B FP32 weight matrix would require approximately 8 exabytes before optimizer state or runtime overhead. This project therefore uses sparse active edges, virtual connection addressing, bounded expert modules, and incremental checkpoints.

The initial implementation is a small, executable research prototype. It does not instantiate one billion neurons or two billion physical weights.

## Architecture milestones

- 00-foundation: project metadata, configuration, reproducibility.
- 01-sparse-engine: bounded sparse graph and message passing.
- 02-virtual-matrix: deterministic virtual connection address space.
- 03-expert-routing: independent experts and top-k routing.
- 04-combined-training: parallel expert batches and incremental updates.
- 05-validation: tests, examples, and resource limits.

## Quick start

Python 3.10+; no third-party runtime dependencies are required for the core prototype.

The CLI and training pipeline will be added in subsequent milestones.
