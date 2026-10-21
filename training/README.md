# Deta 400k staged fine-tuning run

A push to the deta-ai-foundation branch whose commit message contains [train-deta] starts this job after the complete Python CI suite passes.

## Training profile

- Architecture: DetaFiveGroupModel
- Trainable parameters: 400,000 total
- Training schedule: five sequential groups, 80,000 parameters per group
- Updates: 5,000 per group, 25,000 new optimizer updates total
- Initialization: warm-start from the previous verified final.pt checkpoint
- Seed: 42
- Corpus: source files collected from 20 candidate public GitHub repositories; up to 20 files per repository, with allowlisted repository licenses, file-level SPDX checks when present, sensitive-content filtering, provenance and exact deduplication
- Corpus ceiling: 64 MiB
- Validation: the same held-out batch reused across all groups in this training pass
- Checkpoints: group-01.pt through group-05.pt, plus final.pt after group 5
- Provenance: parent checkpoint SHA-256, parent cumulative steps, prior dataset SHA-256, current dataset manifest SHA-256, configuration and per-group loss metrics

The existing checkpoint is loaded before training starts. The new approved corpus is validated independently; public-web retrieval notes are not silently injected into training.

The CI test job must succeed before training starts. This run does not invoke the Android build or modify the APK. On completion, GitHub Actions uploads the checkpoints, approved JSONL manifest and source report as an artifact.

This remains a bounded, code-focused research run, not training on every publicly accessible repository or all AI datasets. Dataset terms, licenses, attribution and removal policies remain in force.
