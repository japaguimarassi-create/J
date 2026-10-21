# Deta 400k staged training run

A push to the deta-ai-foundation branch whose commit message contains [train-deta] runs the staged training job after the full CI suite passes.

The pinned training profile for this run is:
- Architecture: DetaFiveGroupModel
- Total parameters: 400,000
- Sequential groups: five, 80,000 parameters each
- Steps: 1,000 per group
- Seed: 42
- Corpus: bounded source-code files from public GitHub repositories with allowlisted repository licenses, file-level SPDX checks when present, secret-pattern exclusion, provenance and deduplication
- Checkpoints: saved after every group; final.pt is written when group 5 completes
- Output: GitHub Actions artifact containing checkpoints, the approved JSONL manifest and the per-source collection report

Each subsequent group is trained only after the prior group has completed and been checkpointed. The approved manifest hash, training seed, corpus budget and model configuration must remain unchanged when resuming from an earlier group checkpoint.

This is a bounded initial code-only training run. It does not claim to consume every public repository or every external AI dataset. No Android build or APK output is part of this workflow.
