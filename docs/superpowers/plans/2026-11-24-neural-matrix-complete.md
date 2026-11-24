# Neural Matrix Complete Runtime Implementation Plan

> For agentic workers: use the executing-plans workflow. Steps use checkbox syntax for tracking.

**Goal:** Make Neural Matrix an installable vector-learning toolkit with streaming data, a high-level inference/training API, evaluation, reliable checkpoints, a complete CLI, and automated verification.

**Architecture:** Keep the current sparse/virtual/expert engine and wrap it with focused modules for data, model lifecycle, metrics, evaluation, and checkpoint I/O. The CLI streams bounded minibatches and calls the public model API; the standard library remains the only runtime dependency.

**Tech Stack:** Python 3.10+, standard library, unittest, setuptools, GitHub Actions.

**Spec:** docs/superpowers/specs/2026-11-24-neural-matrix-complete-design.md

## Global Constraints

- Python 3.10+.
- Zero third-party runtime dependencies.
- Logical dimensions: 1,000,000,000 rows × 2,000,000,000 columns; virtual address space only.
- Active memory, cache, dataset batches, and workers remain explicitly bounded.
- Existing compatible trainer checkpoints remain readable.
- Do not modify main or merge any branch automatically.

## Review Focus

- Empty JSONL and malformed or non-object records return line-numbered errors, not tracebacks.
- NaN, Infinity, booleans, and mismatched input/target widths are rejected before training or inference.
- A large dataset is streamed in bounded batches and can be replayed for multiple epochs.
- A partially corrupt or incompatible checkpoint never partially mutates an existing model.
- Distributed training handles fewer samples than experts and worker counts above available experts.

---

### Task 1: Dataset streaming and validation

Files: create neural-matrix/src/neural_matrix/data.py; modify neural-matrix/tests/test_core.py.

Interfaces: iter_jsonl(path, input_width, target_width, limit=None) yields (list[float], list[float]); iter_batches(samples, batch_size) yields bounded lists.

- [ ] Add tests for valid JSONL, malformed lines, non-finite values, boolean values, width mismatch, limits, empty files, and bounded batches.
- [ ] Run focused tests and confirm missing functions fail.
- [ ] Implement streaming parsing and validation with line-numbered errors.
- [ ] Run focused tests and the full suite.

### Task 2: Checkpoint format and model API

Files: create checkpoint.py and model.py; modify training.py and test_core.py.

Interfaces: NeuralMatrixModel(config=None), predict(inputs), train_sample(sample), train_batch(samples, mode, workers=None), save(path), load(path), and load_model(path). load_model reconstructs saved configuration; checkpoint read validates the entire payload before changing model state.

- [ ] Add tests for prediction, finite inputs, learning updates, save/load round-trip, metadata mismatch, corrupt checkpoint rejection, and old trainer-checkpoint compatibility.
- [ ] Run focused tests and confirm missing model/checkpoint APIs fail.
- [ ] Implement the model facade and atomic checkpoint helpers.
- [ ] Run focused tests and the full suite.

### Task 3: Evaluation metrics

Files: create metrics.py and evaluation.py; modify test_core.py.

Interfaces: RegressionMetrics.update(prediction, target), RegressionMetrics.to_dict(), and evaluate(model, samples, limit=None) returning sample count, MSE, and MAE.

- [ ] Add tests for hand-calculated MSE/MAE, multiple samples, empty input, and dimension mismatch.
- [ ] Run focused tests and confirm they fail for missing metrics.
- [ ] Implement streaming metrics and evaluation.
- [ ] Run focused tests and the full suite.

### Task 4: Complete command-line workflow

Files: modify cli.py and test_core.py.

Interfaces: add train --epochs --batch-size, predict --checkpoint --input, and evaluate --checkpoint --data; preserve inspect and plan. All success output is JSON; invalid input returns non-zero with an actionable message.

- [ ] Add command tests using real temporary JSONL and checkpoints for train, resume, predict, and evaluate.
- [ ] Run focused tests and confirm new command behavior is absent.
- [ ] Implement bounded epoch/batch training and prediction/evaluation.
- [ ] Run all tests and smoke-test every command.

### Task 5: Packaging, docs, and CI closure

Files: modify pyproject.toml, README.md, config.example.json, and .github/workflows/neural-matrix.yml; create LICENSE and .gitignore.

- [ ] Add exact install/use examples and resource-limit warnings.
- [ ] Add CI steps for unit tests and CLI smoke tests on Python 3.10 and 3.12.
- [ ] Validate package metadata and example configuration.
- [ ] Compare the final branch against its base and inspect all modified files.

## Commit boundaries

- Task 1: feat: stream and validate training datasets
- Task 2: feat: expose model API and robust checkpoints
- Task 3: feat: add streaming regression evaluation
- Task 4: feat: complete train predict evaluate CLI
- Task 5: docs: finalize packaging and automated validation