# Neural Matrix 1B × 2B — Complete Project Design

## Intent

Turn the research scaffold into a self-contained, installable, testable neural-network toolkit for bounded vector-to-vector learning. Preserve the hybrid logical architecture: one billion logical rows by two billion logical columns, sparse physical activation, virtual connection addressing, specialist experts, and combined training.

## Goals

- Python 3.10+ and zero third-party runtime dependencies.
- Reusable APIs for prediction, incremental learning, minibatch training, evaluation, and checkpoint persistence.
- Streaming JSONL input with dimensional and finite-number validation.
- Deterministic synthetic datasets for a complete offline demo.
- CLI commands for generation, inspection, capacity planning, training, prediction, and evaluation.
- Reproducibility through explicit seeds and checkpointed configuration.
- Bounded active memory, virtual-weight cache, dataset batches, and worker counts.
- CI tests and command-level smoke tests on Python 3.10 and 3.12.
- Practical mobile/Termux usage with conservative CPU and memory limits.

## Non-goals

- Claiming 1,000,000,000 physical neurons or 2 × 10¹⁸ trained physical weights.
- Building a general-purpose language model, tokenizer, text-generation stack, or conversational agent.
- Automatically downloading training data or calling external AI APIs.
- Claiming local multiprocessing is a multi-machine cluster.
- Allocating a dense tensor matching the virtual address space.

## Constraints

- Virtual shape: 1,000,000,000 × 2,000,000,000, equal to 2 × 10¹⁸ addressable positions.
- Active graph, cache, data batches, and workers stay inside explicit configuration limits.
- Core execution uses only the Python standard library.
- Compatible legacy trainer checkpoints remain loadable when their dimensions match.
- Main and prior milestone branches remain unchanged pending review and merge.

## Approaches

1. A script-only prototype is easy to start but lacks a reusable API, evaluation, robust checkpointing, and modular data pipeline.
2. PyTorch provides mature tensor kernels but adds a large runtime dependency and does not make the virtual dense matrix physically feasible.
3. A modular, dependency-free Python implementation atop the sparse/virtual/expert engine is selected for portability, testability, and mobile practicality.

## Architecture

- `data.py`: JSONL validation, streaming iteration, bounded batches.
- `synthetic.py`: deterministic teacher-generated vector-regression datasets.
- `model.py`: public model lifecycle around virtual-weight encoding, active sparse graph, and expert routing.
- `metrics.py` and `evaluation.py`: streaming regression metrics and evaluation.
- `checkpoint.py`: atomic checkpoint I/O, format checks, compatibility metadata.
- `cli.py` and `__main__.py`: generate, train, predict, evaluate, inspect, plan, and module entry point.
- Existing memory budgets, capacity planning, expert models, and local process workers provide the lower-level engine.
- GitHub Actions installs the package, runs tests, and executes the complete synthetic-data workflow.

## Acceptance criteria

- A user can install the package, inspect capacity, generate data, train, save/resume, predict, and evaluate.
- Training reads bounded batches rather than holding the entire JSONL dataset in memory.
- Malformed JSONL, wrong widths, non-finite values, missing/incompatible checkpoints, and memory-limit violations fail with actionable errors.
- Checkpoint loading validates the complete state before mutating expert parameters.
- Equal seeds/configs produce deterministic initialization, synthetic data, and predictions.
- CI exercises all unit tests and all public CLI workflows on both supported Python versions.
- Documentation distinguishes the virtual logical address space from physical parameters actually allocated and trained.
