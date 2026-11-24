# Neural Matrix 1B × 2B

Hybrid sparse/virtual neural architecture prototype with routed experts, incremental learning, local process-based training, memory budgets, and progressive capacity planning.

## What the scale means

The configuration describes a virtual address space with **1,000,000,000 rows × 2,000,000,000 columns**, or **2 × 10¹⁸ addressable matrix positions**. This is an address space, not a physically allocated neural network. A dense FP32 matrix of that size would require about **8 exabytes** for weights alone. The prototype never allocates that tensor and does not claim to instantiate one billion physical neurons or two quintillion physical weights.

The default runtime is deliberately small: 256 active graph units, up to 2,048 active edges, and 8 experts of width 32. These are bounded working resources independent of the virtual dimensions.

## Components

- **Sparse graph:** stores only active edges and rejects writes after its configured edge budget is reached.
- **Virtual matrix:** maps large logical coordinates to deterministic addresses and deterministic pseudo-weights without allocating the matrix.
- **Expert routing:** chooses the top-k experts for incremental learning and inference.
- **Combined trainer:** supports incremental updates and thread-sharded expert batches.
- **Distributed trainer:** runs independent expert shards in local Python worker processes. It is single-machine multiprocessing, not a remote cluster or internet-connected worker service.
- **Memory budget:** provides an LRU cache, explicit temporary reservations, and a bounded virtual-weight cache.
- **Progressive scaler:** produces verified capacity stages from the configured active baseline to configured maxima, refusing a stage that exceeds the memory limit.
- **Checkpointing:** writes checkpoints atomically and validates dimensions and numeric values when loading.

The memory estimator is conservative planning guidance, not an operating-system guarantee; Python versions and allocator overhead vary. Leave memory headroom for the OS and other applications.

## Quick start

Requires Python 3.10+ and has no third-party runtime dependencies.

```bash
python -m pip install -e ./neural-matrix
neural-matrix inspect
neural-matrix plan
python -m unittest discover -s neural-matrix/tests -v
```

Train a small JSONL dataset (each `x` and `y` vector must match `expert_width`):

```bash
neural-matrix train --data neural-matrix/examples/sample.jsonl --mode incremental
neural-matrix train --data neural-matrix/examples/sample.jsonl --mode parallel
neural-matrix train --data neural-matrix/examples/sample.jsonl --mode distributed --workers 2
```

Use `--config neural-matrix/config.example.json` to select explicit budgets. Reduce `max_workers`, `max_active_units`, `max_active_edges`, and `memory_limit_mb` on memory- or battery-constrained devices. The distributed mode has process-startup overhead and may be slower for tiny datasets.

## Capacity roadmap

`neural-matrix plan` prints bounded growth stages. Each stage doubles active units and edges (clamped to configured maxima) and is checked against the memory estimator before it is included. Expanding the logical address space does not automatically allocate physical resources.

## Validation

The test suite covers virtual addressing, sparse limits, expert updates, checkpoint round-trips, cache eviction, capacity planning, and local process-based training. GitHub Actions runs the suite on pushes and pull requests. A green result should be claimed only after the corresponding workflow run has completed successfully.

## Current limitations

This is a research scaffold, not a trained general-purpose language model. It currently implements a small tanh expert model for vector-to-vector samples. It does not contain billion-scale learned parameters, GPU kernels, multi-machine networking, automatic data acquisition, or a tokenizer/text-generation stack. Those require separate engineering and substantial compute/data resources.
