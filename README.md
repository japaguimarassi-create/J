# Deta

Deta is an experimental foundation for an AI developer that searches public resources, tracks provenance, learns incrementally from authorized data, and evaluates code through four independent gates. This branch contains the software foundation only. No Android application or APK has been generated.

## Initial targets

- A byte-level recurrent model with **79,824 actual trainable parameters**, close to the 80,000-parameter target.
- **10,000 conceptual action units** as an architectural abstraction, not literal neurons and not part of the neural parameter count.
- Search for public GitHub repositories and selective source ingestion after license checks.
- Dataset records that preserve URL, SPDX license, path and SHA-256 digest.
- Incremental training and local checkpoints.
- Four verification gates: syntax, static security checks, explicit tests, and provenance/license/similarity checks.
- Python continuous integration. No Android build workflow.

A model with about 80,000 trainable parameters cannot, by itself, be a capable general-purpose AI or absorb “all AI training.” This small model is a byte-prediction research baseline. Practical capabilities must come from retrieval, tools, planning, tested workflows and later models. Large-scale training also requires much more compute, carefully governed data and reliable evaluation.

Publicly reachable data is not automatically free to use. Deta rejects unknown licenses, does not seek private data or credentials, and does not bypass dataset access agreements, attribution requirements or opt-out/removal processes. The dataset catalog is a starting inventory, not a claim that every dataset is accessible or approved.

## Requirements

- Python 3.11+
- PyTorch 2.2+
- pytest for tests
- Internet for GitHub API queries; the unauthenticated API has limited quotas.

## Install and test

    python -m venv .venv
    source .venv/bin/activate
    python -m pip install -e ".[dev]"
    python -m deta.cli doctor
    python -m deta.cli count-params
    python -m pytest -q

PyTorch wheels may not be available for every Android/Termux configuration. Start model training on a supported Linux runner or environment.

## Search public projects

    python -m deta.cli search-github --query "godot platformer" --limit 5
    python -m deta.cli ingest-github --repo OWNER/REPO --max-files 10 --output data/approved.jsonl

The ingestion command checks repository license metadata before requesting a bounded set of text source files. It rejects missing or unsupported licenses. Review the original project’s LICENSE and notices before using or redistributing code.

## Train the baseline

Create a JSONL manifest where each row includes content, source_url, license_id and source_type (code or text). Deta filters records before they enter the corpus.

    python -m deta.cli train --data data/approved.jsonl --output checkpoints/deta-byte-gru.pt --steps 1000

This trains the small byte-level model; it does not download all online datasets.

## Four verification gates

1. Syntax and supported data-format validation.
2. Static checks for selected risky constructs and embedded credentials.
3. Tests by an explicitly configured runner. The verifier does not execute generated code by default.
4. Reference URL/license checks and similarity against known reference snippets.

These checks reduce risk but do not prove the absence of all bugs. Run untrusted code only in a disposable sandbox without secrets or production permissions.

See docs/DATA_GOVERNANCE.md and docs/RESEARCH.md for data policy and sources.

## APK status

**No APK has been created.** Android app implementation and APK build automation remain out of scope until the user explicitly authorizes APK creation. The current CI only checks the Python foundation.
