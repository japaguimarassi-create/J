# Deta architecture

## Current baseline

The current branch is a Python research foundation with a deliberately small byte-level GRU. Default dimensions are vocabulary=256, embedding=64 and hidden size=88, resulting in 79,824 trainable parameters. The 10,000 conceptual action units are a separate design abstraction and are not counted as model parameters.

## Subsystems

- **Source catalog:** public GitHub repository metadata search and selective source-file fetch.
- **License gate:** rejects unknown or unsupported repository license identifiers before downloading code.
- **Dataset manifest:** records source URL, license, repository/path and content SHA-256; exact duplicates are removed; manifest writes are atomic.
- **Training:** corpus-size bound, deterministic seed, train/validation split, finite-loss check, gradient clipping, atomic checkpoint writes and optimizer-state resume.
- **Verification:** supported-format syntax checks, static risky-pattern checks, explicitly supplied tests, and source/license/similarity checks.
- **CI:** dependency consistency, bytecode compilation, focused static checks, parameter-count smoke test and unit tests.

## Four independent verification gates

1. Syntax and format parsing for Python, JSON and TOML.
2. Configured static security patterns.
3. Tests; this gate fails when no test runner is provided.
4. Source URL/license validation and token-shingle similarity review.

This is a useful engineering gate, not a proof of correctness, legal compliance or security. The static checks are pattern-based and can both miss flaws and produce false positives.

## Growth path

1. Stabilize the baseline and require passing CI.
2. Add held-out coding/planning benchmarks and regression tracking.
3. Add reviewed search connectors for approved dataset registries and documentation sources.
4. Add a task planner and constrained tool interfaces with explicit permission policies.
5. Add sandboxed project generation for games and social apps.
6. Design Android packaging separately, and only after the user explicitly authorizes APK creation.

## Model and data limits

The baseline is not a general-purpose language model. Larger-model training requires considerably more parameters, clean and representative data, compute, evaluation, and well-described dataset governance. Candidate sources in the registry are not automatically downloaded. Terms, attribution, access agreements, opt-outs and removal policies must be honored.
