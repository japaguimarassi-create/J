# Data governance and training policy

## Default rule

A dataset or repository is not training-eligible merely because it can be viewed or downloaded. Every example must have a source URL, license identifier, source type and content hash. Unknown licenses are rejected. Preserve provenance for every retained record.

## Code allowlist

The initial code allowlist is 0BSD, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, MIT and Unlicense. This is a conservative software policy, not legal advice; projects may contain additional notices, dual licenses, submodules, generated files or non-code assets. Inspect the original repository license and notices before redistribution.

The text-data allowlist is separate: CC0-1.0, CC-BY-4.0, ODC-BY-1.0 and Public-Domain. Terms of the specific dataset still govern access, attribution, privacy and redistribution.

## Public-source ingestion

- Search repository metadata first.
- Check explicit SPDX license metadata before requesting file contents.
- Fetch only a bounded number of source files; skip binaries, lockfiles, minified assets, environment files and files with credential-like names.
- Store source URL, repository, path, license and SHA-256 digest.
- Reject unknown or unsupported licenses.
- Deduplicate identical content.
- Do not collect private repositories, credentials or authentication material.
- Respect rate limits, source terms, takedown requests, dataset opt-outs and removal updates.

These controls cannot detect every secret or every licensing issue. Review the original project's terms before using or redistributing generated artifacts.

## Large datasets and “all available training”

No system can truthfully promise to obtain all AI training datasets. Some are proprietary, access-restricted, unavailable, revoked, too large or governed by terms that limit use. Deta keeps a catalogue of candidate sources; each source must be enabled and checked separately. The Stack v2 documents an agreement requirement for bulk content. Deta must not bypass it.

## Incremental learning

Training consumes a curated JSONL manifest. Each record is validated. Keep source and dataset versions beside checkpoints; do not merge new data invisibly into a checkpoint. Later versions should use repeatable seeds and held-out evaluation splits to measure improvement and regressions.

## Generated-code review

The four-pass verifier is a gate, not proof of security or correctness:
1. Syntax and supported format validation.
2. Static patterns for common risky constructs and hardcoded credentials.
3. Explicit tests in a restricted runner.
4. Provenance, license metadata and similarity checks.

Do not execute generated code with personal tokens, production credentials, unrestricted networking or host filesystem privileges. Similarity checks detect only some overlap; they do not decide legal questions.
