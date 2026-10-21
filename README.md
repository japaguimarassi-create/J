# Deta AI 0.2.0

Deta is an experimental foundation for an AI developer that discovers public code, tracks source and license metadata, trains a compact grouped language model, and verifies software through four separate gates. This is the research/core version; the Android app and APK packaging have not been created.

## Model target

- **400,000 actual trainable parameters**, measured from the default model.
- **Five sequential groups**, each with exactly **80,000 parameters**.
- A retained **79,824-parameter baseline** to compare against the grouped model.
- **50,000 conceptual action units** as an architecture planning abstraction, not literal neurons and not part of the neural parameter count.

Groups 2–5 start with zero-output residual heads. Deta trains group 1 first, then freezes it while training group 2 to refine the combined output, and continues the same process through group 5. Every completed group gets its own checkpoint. The final model is the sum of all five groups.

The parameter count does not imply broad capability. This is a small byte-level experiment, not a substitute for a modern pretrained general-purpose model. Real coding ability depends on data quality, architecture, training compute, evaluation, retrieval and tools.

## Features in this branch

- Public GitHub repository search and bounded source ingestion.
- Per-repository license allowlist plus per-file SPDX checks when present.
- Sensitive-token/private-key pattern filtering, exact-content deduplication and SHA-256 provenance.
- GitHub API retry/backoff for rate limits and network failures, with bounded waits.
- Five-stage sequential training, deterministic per-group seeds, validation loss and restartable checkpoints.
- Resume checks for architecture, previous group number and exact dataset-manifest hash.
- Four-pass verification: syntax/format, static security patterns, explicit tests, and provenance/license/similarity.
- GitHub Actions CI and an optional training job that stores all stage checkpoints as a workflow artifact.

## Install and test

Python 3.11+ and PyTorch 2.2+ are required. Development checks use pytest and Ruff.

    python -m venv .venv
    source .venv/bin/activate
    python -m pip install -e ".[dev]"
    python -m deta.cli doctor
    python -m deta.cli count-params
    python -m pytest -q
    python -m ruff check --select E4,E7,E9,F401,F63,F7,F82 deta tests scripts

PyTorch wheels may not be available for every Android/Termux configuration. Use a supported Linux runner or environment for training.

## Prepare a bounded, approved code corpus

    python scripts/build_training_corpus.py --output data/approved.jsonl --max-files-per-repo 12

The preparer queries a finite list of public GitHub repositories and downloads a bounded number of source files only when GitHub reports an allowlisted license. It checks file-level SPDX declarations when present and excludes common secret patterns and credential-like paths. Results include source URLs, detected license IDs, paths and content hashes. Failed or unsupported repositories are recorded in data/approved.report.json; the workflow fails if it cannot collect enough unique eligible records.

This is an initial code-only sample, not the entire internet and not all public training data. The source registry describes additional candidate datasets. Some are too large for this prototype or have access agreements. For example, The Stack v2 card says bulk source-content access requires an agreement with Software Heritage and INRIA; Deta does not bypass that gate. Always honor source licenses, attribution, opt-out and removal policies. See docs/DATA_GOVERNANCE.md and docs/RESEARCH.md.

For GitHub API rate limits, an optional DETA_GITHUB_TOKEN environment variable can authenticate API calls. Never store the token in Git or a corpus manifest. Authentication is restricted to api.github.com; file downloads from raw.githubusercontent.com never receive this token.

## Train all five groups sequentially

    python -m deta.cli train --data data/approved.jsonl --output-dir checkpoints/deta-400k --steps-per-group 1000 --start-group 1 --end-group 5 --seed 42

The CLI trains one 80k group at a time. It records the last training loss and validation loss after each group and writes:

- group-01.pt after group 1
- group-02.pt after group 2
- group-03.pt after group 3
- group-04.pt after group 4
- group-05.pt and final.pt after group 5

To resume after group 3, keep the exact same approved manifest and architecture:

    python -m deta.cli train --data data/approved.jsonl --output-dir checkpoints/deta-400k --steps-per-group 1000 --start-group 4 --end-group 5 --resume-from checkpoints/deta-400k/group-03.pt --seed 42

Resume is intentionally rejected if the dataset manifest hash, model configuration or preceding-group number differs. Preserve data/approved.jsonl between resume sessions. Do not rerun the corpus-preparation script before resuming unless the new manifest is meant to start a new training run.

To use a different step count for an experiment, change --steps-per-group. The default corpus ceiling is 64 MiB per run and can be adjusted with --max-bytes after considering available RAM and compute.

## Four-pass verification

    python -m deta.cli verify --project . --run-tests

1. **Syntax and formats:** parse supported Python, JSON and TOML files.
2. **Static security patterns:** flag selected dynamic execution, shell-risk patterns and likely embedded credentials.
3. **Tests:** pass only when an explicit test runner succeeds. Without --run-tests, the gate fails.
4. **Provenance and similarity:** validate reference URLs/license IDs and compare token shingles against provided references.

These checks reduce risk but cannot prove that code is bug-free, secure or legally clear. Do not run untrusted generated code with personal tokens, production credentials or unrestricted permissions.

The legacy 79,824-parameter training baseline remains available via train-baseline; the main train command is the five-group model.

## APK status

**No APK has been created.** The current work is the model/data/verification foundation on GitHub. Android app implementation and any APK packaging/build are deliberately excluded until the user explicitly authorizes that stage.
