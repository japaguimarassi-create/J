# Deta

Deta is an experimental foundation for an AI developer that searches public resources, tracks provenance, learns incrementally from authorized data, and evaluates code through four independent gates. This branch contains the software foundation only. No Android application or APK has been generated.

## Current implementation

- A byte-level recurrent model with **79,824 actual trainable parameters**, near the 80,000 target.
- **10,000 conceptual action units** as an architectural abstraction. They are not literal neurons and are not part of the model's neural parameter count.
- Public GitHub repository search and selective source ingestion after license metadata checks.
- Dataset records with source URL, SPDX license, path and SHA-256 digest.
- Exact-content deduplication and atomic manifest writes.
- Incremental training with a bounded corpus, deterministic seed option, validation loss and resumable checkpoints.
- Four verification gates: syntax, static security checks, explicit tests, and provenance/license/similarity checks.
- GitHub Actions tests, Python compilation and targeted static checks.
- A source catalogue for research into larger text and code datasets.

The small model is a training baseline, not a capable general-purpose AI. Useful coding ability will require retrieval, planning, tools, tested workflows, quality datasets and likely much larger pretrained models. Parameter count alone does not determine capability.

## Requirements

- Python 3.11+
- PyTorch 2.2+
- pytest and Ruff for development checks
- Internet access for the public GitHub API. Set DETA_GITHUB_TOKEN in the environment to use your own token and higher API quotas; never commit the token.

## Install and test

    python -m venv .venv
    source .venv/bin/activate
    python -m pip install -e ".[dev]"
    python -m deta.cli doctor
    python -m deta.cli count-params
    python -m pytest -q
    python -m ruff check --select E4,E7,E9,F401,F63,F7,F82 deta tests

PyTorch wheels may not be available for every Android/Termux environment. Use a supported Linux runner or machine for the initial training workflow.

## Search public projects

    python -m deta.cli search-github --query "godot platformer" --limit 5
    python -m deta.cli ingest-github --repo OWNER/REPO --max-files 10 --output data/approved.jsonl

The ingestion command requires the repository API to report an approved SPDX license before it requests a bounded selection of source files. It does not pass a GitHub API token to raw file hosts. Repository-level license metadata is a first filter, not proof that every file or third-party asset is covered by that license. Review the original project's LICENSE, notices, file-level terms and dataset policies before use or redistribution.

Unknown licenses are rejected. Private repositories, secrets and credential files are not target data. Do not bypass rate limits, access gates, dataset agreements or opt-out/removal policies.

## Train and resume the baseline

Create a JSONL manifest with one record per example. Each record must include content, source_url, license_id and source_type (code or text). Deta validates the manifest before consuming examples.

    python -m deta.cli train --data data/approved.jsonl --output checkpoints/deta-byte-gru.pt --steps 1000 --seed 42

Continue training from a prior checkpoint with more approved data:

    python -m deta.cli train --data data/approved.jsonl --output checkpoints/deta-byte-gru.pt --resume-from checkpoints/deta-byte-gru.pt --steps 500 --seed 42

The default corpus ceiling is 64 MiB per run. Adjust it with --max-bytes after considering available RAM and compute. A resumed checkpoint must match the architecture used to train it. Training is performed on CPU unless a supported CUDA device is available or selected.

This command trains the small byte-level model; it does not download every dataset from the internet or turn the model into general intelligence.

## Four verification gates

1. **Syntax and formats:** parse Python, JSON and TOML files that are part of the bundle.
2. **Static checks:** search for selected risky constructs and hardcoded credential patterns.
3. **Tests:** require an explicit test runner. If tests have not run, the gate stays failed.
4. **Provenance and similarity:** inspect source URLs, license identifiers and token-shingle overlap with known references.

These checks reduce errors but cannot prove that a project is bug-free or secure. Untrusted generated code should run only in a disposable sandbox without personal tokens, production credentials, unrestricted network access or privileged host access.

## Dataset scale and permissions

The source list includes FineWeb/FineWeb2 and The Stack as research candidates, not as content automatically downloaded by Deta. FineWeb is a very large corpus under ODC-BY 1.0; The Stack v2 has source-level licenses and its card states that bulk file-content access requires an agreement with Software Heritage and INRIA. Read current source pages, use manageable subsets, preserve attribution and honor removal requests.

See docs/DATA_GOVERNANCE.md and docs/RESEARCH.md for details.

## APK status

**No APK has been created.** Android app implementation and APK build automation remain out of scope until the user explicitly authorizes APK creation. The current CI only checks the Python foundation.
