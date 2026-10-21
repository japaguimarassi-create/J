# Deta architecture 0.2.0

## Parameter layout

The default model contains exactly 400,000 trainable parameters in five groups. Each group uses a byte embedding, GRU, trainable hidden scale/bias and output projection, with 80,000 parameters per group. The earlier standalone byte-GRU baseline remains available with 79,824 parameters.

Later groups start with zero-output residual heads so that the untrained groups do not perturb the active model. Training proceeds in order:
1. Train group 1 against the approved byte corpus.
2. Freeze groups already trained and train group 2 on the combined logits.
3. Repeat for groups 3, 4 and 5.
4. After each group, write an atomic checkpoint with model weights, configuration, dataset hash, group metrics and completed-group count.

A checkpoint from group N is valid for starting group N+1 only when the architecture/configuration and full manifest SHA-256 match. Each group resets its optimizer rather than transferring optimizer moments between distinct parameter groups.

## Components

- **Public-source catalog:** searches public GitHub repository metadata and selectively fetches source files after repository license metadata checks.
- **Source filter:** rejects unsupported licenses; honors file-level SPDX declarations when present; excludes likely private key/token/password content, common credential paths, generated/binary-like files and oversized files.
- **Provenance manifest:** stores source URL, license identifier, repository/path and content digest; deduplicates exact content and writes manifests atomically.
- **Five-group model:** sums the outputs of up to five independent experts. Each completed stage is frozen for subsequent training.
- **Training engine:** bounded corpus loading, deterministic stage seeds, train/validation split, finite-loss checks, gradient clipping, validation metrics, stage-by-stage and final checkpoints, strict resume checks.
- **Four-pass verifier:** supported-format syntax, static risky-pattern checks, explicit tests and source/license/similarity checks.
- **CI and training workflow:** every change runs packaging/dependency checks and tests. The heavy training job runs only on the specially tagged commit, waits for CI to pass and uploads checkpoints as artifacts.

## Four independent verification gates

1. Parse Python, JSON and TOML syntax in a bounded project scan.
2. Check configured static security patterns.
3. Run tests only when explicitly requested against a trusted project.
4. Validate reference URL/license metadata and token-shingle similarity.

Pattern-based checks can miss problems and produce false positives. A passing report is not a proof of correctness, security or copyright compliance.

## Data and model limits

The active training job gathers a finite, bounded sample from a curated list of public GitHub projects whose repository license metadata is on Deta's allowlist. It is not a universal web crawler and it does not download every AI dataset. Dataset catalog entries such as FineWeb and The Stack v2 have their own size, access, attribution, license and removal constraints.

A 400k-parameter byte-level model is a controlled experiment, not a modern general-purpose AI. Larger models, more compute, quality benchmarks, retrieval and safe tool interfaces are future work.

## Next implementation phases

1. Confirm test and training-run reproducibility.
2. Add held-out coding/logic benchmarks and regression comparisons between groups.
3. Add reviewed connectors for more public dataset indexes and documentation.
4. Implement a task planner and tool adapters with narrow permissions.
5. Generate complete game/app projects in disposable workspaces.
6. Only after explicit user authorization, begin Android UI and APK packaging.
