# Data governance and training policy

## Default rule

A dataset or repository is not training-eligible merely because it can be viewed or downloaded. Every training example must have a source URL, license identifier, source type and content hash. Unknown licenses are rejected. Preserve provenance for every retained training record.

## Code allowlist

The initial code allowlist is 0BSD, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, MIT and Unlicense. This is a conservative software policy, not legal advice; repositories can contain additional notices, dual licenses, submodules, generated files or third-party assets. Inspect the source project's license and notices before using or redistributing code.

The text-data allowlist is separate: CC0-1.0, CC-BY-4.0, ODC-BY-1.0 and Public-Domain. Terms of each dataset still govern access, attribution, privacy and redistribution.

## Public-source training ingestion

- Search repository metadata first.
- Check explicit SPDX license metadata before requesting file contents.
- Fetch a bounded number of source files; skip common credential paths, environment files, lockfiles, minified assets and oversized files.
- Honor file-level SPDX identifiers when present; reject non-allowlisted or ambiguous expressions.
- Store source URL, repository, path, license and SHA-256 digest.
- Deduplicate exact content.
- Do not collect private repositories, credentials or authentication material.
- Respect source terms, rate limits, dataset opt-outs, takedown requests and removal updates.

These controls cannot detect every secret or licensing issue. Review the original source project before using or redistributing generated artifacts.

## Web retrieval is separate from training

Deta's public-web research searches DuckDuckGo public HTML results and fetches publicly accessible HTTPS pages without a hosted generative-AI API. Search terms are sent to the search engine; page reads go directly to source websites. Some sites block automated reads, and Deta does not log in or bypass access controls.

Extracted pages are saved in the local knowledge index for retrieval with source links and hashes. They are **not automatically used to train the neural model**. To include a web dataset in training, it must separately pass the license allowlist, terms, attribution, privacy and opt-out checks.

## Large datasets and “all available training”

No system can truthfully promise to obtain all AI training datasets. Some are proprietary, access-restricted, unavailable, revoked, too large or governed by terms that limit use. Deta keeps a catalogue of candidate sources; each source must be enabled and checked separately. The Stack v2 documents an agreement requirement for bulk content access. Deta must not bypass it.

## Incremental learning

Training consumes a curated JSONL manifest. Each record is validated. Checkpoints retain source/dataset hashes and training lineage; do not merge new data invisibly into an existing checkpoint. Warm-start fine-tuning records the parent checkpoint hash, previous training step count and previous dataset hash. Keep held-out evaluation data separate from training data.

## Generated-code review

The four-pass verifier is a gate, not proof of security or correctness:
1. Syntax and supported-format validation.
2. Static checks for common risky constructs and hardcoded credentials.
3. Explicit tests in a restricted runner.
4. Provenance, license metadata and similarity checks.

Do not execute generated code with personal tokens, production credentials, unrestricted networking or host filesystem privileges.

## Local knowledge storage

The retrieval index is stored in ~/.local/share/deta/knowledge.json by default, or under DETA_HOME if set. It stores extracted page text, source URLs and content hashes. Inspect it with the knowledge command, search it with the knowledge --query option, or remove it with clear-knowledge --yes. Clearing the knowledge index does not remove model checkpoints or training manifests.
