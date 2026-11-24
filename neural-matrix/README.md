# Neural Matrix 1B × 2B

Neural Matrix is a dependency-free Python toolkit for bounded vector-to-vector neural learning. It combines a virtual logical matrix, an active sparse graph, routed specialist networks, incremental and minibatch training, local process workers, checkpoints, evaluation, and a command-line workflow.

## What 1B × 2B means

The logical address space is configured as **1,000,000,000 rows × 2,000,000,000 columns**, equal to **2 × 10¹⁸ addressable positions**. This is virtual addressing, not a dense array allocated in memory. A dense FP32 matrix of that shape would require roughly **8 exabytes** for weights alone.

The implementation does not claim to contain one billion physical neurons or two quintillion trained physical weights. The default active system is deliberately bounded: 256 active graph units, up to 2,048 configured sparse edges, 8 tanh experts of width 32, and top-2 expert routing. The sparse graph is part of the actual input-encoding path; its weights are addressed through the virtual matrix and held in a bounded cache.

## Features

- **Virtual matrix:** stable logical row/column addressing and deterministic pseudo-weights without allocating a dense tensor.
- **Sparse graph:** active edges sampled from virtual coordinates, bounded by a configured edge budget.
- **Routed experts:** independent small tanh networks with deterministic top-k routing.
- **Training modes:** incremental updates, thread-parallel expert batches, and local multiprocessing across expert shards.
- **Streaming datasets:** JSONL parsed line by line, with finite-number checks and fixed vector dimensions.
- **Synthetic data:** seeded vector-regression dataset generation for a reproducible end-to-end smoke test.
- **Inference and evaluation:** prediction, MSE, MAE, and sample counts.
- **Checkpoints:** atomic writes, compatibility checks, and validation before loading state.
- **Resource planning:** LRU virtual-weight cache, explicit memory reservations, bounded workers, and a progressive active-capacity plan.
- **CLI:** generate, inspect, plan, train, predict, and evaluate.

## Requirements

- Python 3.10 or newer.
- No third-party runtime dependencies.
- Setuptools is used only to install the package.
- CPU-only implementation; no GPU kernel is included.

## Install

From the repository root:

```bash
python -m pip install -e ./neural-matrix
```

You can also execute without the installed console command:

```bash
cd neural-matrix
python -m pip install -e .
python -m neural_matrix inspect
```

## Complete demo

Run these commands from the repository root after installation:

```bash
neural-matrix inspect
neural-matrix plan
neural-matrix generate --output neural-matrix/examples/demo.jsonl --samples 512 --width 32 --seed 17
neural-matrix train --data neural-matrix/examples/demo.jsonl --checkpoint neural-matrix/checkpoints/demo.json --epochs 5 --batch-size 16 --mode incremental
neural-matrix evaluate --checkpoint neural-matrix/checkpoints/demo.json --data neural-matrix/examples/demo.jsonl
```

For a prediction, take one input vector from the generated JSONL file:

```bash
INPUT=$(python -c 'import json; print(json.dumps(json.loads(open("neural-matrix/examples/demo.jsonl").readline())["x"]))')
neural-matrix predict --checkpoint neural-matrix/checkpoints/demo.json --input "$INPUT"
```

The generator, training and evaluation all use the same fixed-width vectors. When using a custom config, generate data with its expert_width.

## Android / Termux

A conservative mobile workflow uses incremental training and small batches. From Termux:

```bash
pkg update
pkg install python git
git clone https://github.com/japaguimarassi-create/J.git
cd J/neural-matrix
python -m pip install -e .
python -m neural_matrix inspect
python -m neural_matrix generate --output demo.jsonl --samples 128 --width 32
python -m neural_matrix train --data demo.jsonl --checkpoint checkpoints/model.json --epochs 2 --batch-size 4 --mode incremental
python -m neural_matrix evaluate --checkpoint checkpoints/model.json --data demo.jsonl
```

Incremental mode is the recommended default on a phone. Thread parallelism may not improve small workloads. The distributed mode uses local Python processes, has process-startup and memory overhead, and is not a multi-machine cluster. Reduce batch size, max_workers, max_active_units, max_active_edges, virtual_cache_mb, or memory_limit_mb when the device is constrained.

## Configuration

Copy and edit config.example.json. Important limits:

- active_units and active_edges: current graph allocation ceilings.
- max_active_units and max_active_edges: upper bounds used by the capacity planner.
- memory_limit_mb: planning budget for active resources.
- virtual_cache_mb: LRU cache ceiling; it cannot exceed the total memory limit.
- max_workers: upper bound for local training workers.
- expert_width, expert_count, and top_k_experts: size and routing of the active expert network.

The memory estimate is conservative planning guidance, not a guarantee of actual process RSS. Python object sizes, allocators, OS activity, and other apps affect real use. Leave memory headroom.

## Python API

```python
from neural_matrix import MatrixConfig, NeuralMatrixModel

config = MatrixConfig(expert_width=4, active_units=16, active_edges=32,
                      max_active_units=32, max_active_edges=64,
                      memory_limit_mb=8, virtual_cache_mb=1)
model = NeuralMatrixModel(config)

loss = model.train_sample(([0.1, 0.2, 0.3, 0.4], [0.0, 0.1, 0.2, 0.3]))
prediction = model.predict([0.1, 0.2, 0.3, 0.4])
model.save("model.json")
```

To restore a complete checkpoint including its configuration:

```python
model = NeuralMatrixModel.from_checkpoint("model.json")
```

## Tests

```bash
python -m unittest discover -s neural-matrix/tests -v
```

GitHub Actions runs the unit suite and command smoke tests on Python 3.10 and 3.12.

## Current limits

This is a small CPU research model for numerical vector regression, not a general-purpose LLM or chatbot. There is no tokenizer, language pretraining corpus, conversational fine-tuning, transformer stack, GPU backend, or multi-machine network transport. Creating those would be separate substantial projects with different compute and data requirements.

No open-source license has been assigned in this branch. The repository owner should choose one before redistributing the software under a specific license.
