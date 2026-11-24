# Neural Matrix 1B × 2B — Complete Project Design

## Intent

Turn the existing Neural Matrix research scaffold into a self-contained, installable, testable neural-network toolkit for bounded vector-to-vector learning. Preserve the user's hybrid logical architecture: one billion logical rows by two billion logical columns, sparse physical activation, virtual address mapping, specialist experts, and combined training.

## Goals

- Keep Python 3.10+ and zero third-party runtime dependencies.
- Provide a stable model API for prediction, incremental learning, minibatch training, evaluation, and checkpoint persistence.
- Read JSONL datasets incrementally, validate dimensions and finite numeric values, and avoid loading large datasets into RAM.
- Offer CLI commands for inspection, capacity planning, training, prediction, and evaluation.
- Preserve reproducibility through explicit seeds and checkpointed configuration.
- Bound active memory, virtual-weight caching, and worker counts.
- Run unit tests and command-level smoke tests in GitHub Actions on Python 3.10 and 3.12.
- Keep the project usable from a Python environment such as Termux, with conservative configurable worker and memory ceilings.

## Non-goals

- Claiming that 1,000,000,000 physical neurons or 2 × 10^18 trained physical weights exist.
- Building a general-purpose language model, tokenizer, text-generation stack, or conversational agent.
- Automatically downloading training data or calling external AI APIs.
- Pretending local multiprocessing is multi-machine distributed computing.
- Allocating a dense tensor matching the virtual address space.

## Constraints

- The virtual shape is 1,000,000,000 × 2,000,000,000; its addressable position count is 2 × 10^18.
- Active graph, cache, and worker resources must stay bounded by explicit configuration.
- Core execution must use only the Python standard library.
- Existing checkpoints without the new optional metadata must remain loadable when dimensions match.
- The main branch and the earlier milestone branches must remain unchanged until a pull request is reviewed and merged.

## Approaches

1. A minimal script-only prototype would be easiest to run but would not provide reusable APIs, evaluation, reliable dataset streaming, or clear component boundaries.
2. A PyTorch-based framework would provide mature tensor kernels but adds a large dependency and increases friction on mobile-only devices; it also does not make the 1B × 2B physical matrix feasible.
3. A modular, dependency-free Python implementation on top of the current sparse/virtual/expert design is selected. It is portable, testable, easy to install, and honest about its physical resource limits.

## Architecture

- data.py: JSONL sample validation, streaming iteration, bounded batching.
- model.py: stable high-level model object around expert routing and training.
- metrics.py and evaluation.py: streaming regression metrics and evaluation.
- checkpoint.py: atomic checkpoint I/O, compatibility checks, and metadata.
- cli.py: train, predict, evaluate, inspect, and plan commands.
- Existing sparse graph, virtual matrix, memory budget, capacity planner, experts, and local process trainer remain as the lower-level engine.
- GitHub Actions provides supported-version tests and command smoke checks.

## Acceptance criteria

- A user can install the package, inspect its logical and active dimensions, create a model, train it on JSONL data, save/resume a checkpoint, run prediction, and evaluate predictions.
- Training reads bounded batches rather than retaining the entire JSONL dataset.
- Wrong vector widths, malformed JSONL, NaN/Infinity, missing checkpoints, incompatible checkpoints, and memory-limit violations fail with actionable errors.
- Predictions and model initialization are deterministic for equal seeds and equal checkpoints.
- CI exercises all tests and all public CLI subcommands.
- Documentation explicitly distinguishes virtual logical capacity from physically allocated and trained parameters.