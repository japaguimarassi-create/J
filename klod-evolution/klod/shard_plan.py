import argparse
import json
from pathlib import Path


TARGET_LAYERS = 40000
TARGET_WIDTH = 60000
TILE_WIDTH = 500
VOCAB_SIZE = 258


PROFILES = {
    "micro": {"layers": 1, "width": 32, "heads": 2, "experts": 2, "seq_len": 64},
    "small": {"layers": 2, "width": 64, "heads": 4, "experts": 2, "seq_len": 128},
    "medium": {"layers": 4, "width": 128, "heads": 4, "experts": 4, "seq_len": 256},
    "large": {"layers": 6, "width": 256, "heads": 8, "experts": 4, "seq_len": 512},
}


def estimate_dense_target(layers: int = TARGET_LAYERS, width: int = TARGET_WIDTH) -> dict:
    if layers < 1 or width < 1:
        raise ValueError("layers and width must be positive")
    parameters = max(0, layers - 1) * width * width
    fp16_bytes = parameters * 2
    tiles_per_axis = (width + TILE_WIDTH - 1) // TILE_WIDTH
    matrix_tiles = max(0, layers - 1) * tiles_per_axis * tiles_per_axis
    return {
        "logical_layers": layers,
        "virtual_neurons_per_layer": width,
        "virtual_neuron_slots": layers * width,
        "dense_weight_parameters_estimate": parameters,
        "fp16_weight_bytes_estimate": fp16_bytes,
        "fp16_weight_decimal_tb_estimate": fp16_bytes / 1_000_000_000_000,
        "fp16_weight_binary_tib_estimate": fp16_bytes / (1024 ** 4),
        "tile_width": TILE_WIDTH,
        "tiles_per_axis": tiles_per_axis,
        "matrix_tiles_per_transition": tiles_per_axis * tiles_per_axis,
        "total_matrix_tiles_estimate": matrix_tiles,
        "weights_per_full_tile": TILE_WIDTH * TILE_WIDTH,
        "fp16_bytes_per_full_tile": TILE_WIDTH * TILE_WIDTH * 2,
        "warning": "Dense matrix tile counts are a storage decomposition only. Training a tile independently does not reproduce end-to-end gradients through the full network."
    }


def estimate_profile(profile: str) -> dict:
    if profile not in PROFILES:
        raise ValueError(f"Unknown profile: {profile}")
    item = PROFILES[profile]
    width = item["width"]
    experts = item["experts"]
    layers = item["layers"]
    seq_len = item["seq_len"]
    embedding = VOCAB_SIZE * width + seq_len * width
    final_norm = 2 * width
    attention = 4 * width * width + 4 * width
    norms = 4 * width
    router = width * experts + experts
    expert_params = experts * (8 * width * width + 5 * width)
    block = attention + norms + router + expert_params
    parameters = embedding + final_norm + layers * block
    return {
        "profile": profile,
        **item,
        "estimated_parameters": parameters,
        "fp32_weights_bytes": parameters * 4,
        "adamw_training_state_floor_bytes": parameters * 16,
        "note": "Approximate model state only. Activations, temporary workspaces, fragmentation and data buffers require additional memory."
    }


def build_plan(domain_count: int = 5) -> dict:
    if domain_count < 1:
        raise ValueError("domain_count must be positive")
    target = estimate_dense_target()
    practical = {
        name: estimate_profile(name)
        for name in PROFILES
    }
    return {
        "name": "KLOD 40k x 60k decomposition plan",
        "target": target,
        "literal_tensor_sharding": {
            "neuron_tile_width": TILE_WIDTH,
            "tiles_per_neuron_axis": target["tiles_per_axis"],
            "tiles_per_dense_layer_transition": target["matrix_tiles_per_transition"],
            "total_weight_tiles": target["total_matrix_tiles_estimate"],
            "trainability": "A tile is small enough to store, but it cannot be trained independently as a faithful part of the complete network without the neighboring activations and end-to-end gradient flow."
        },
        "practical_capability_sharding": {
            "default_domains": [
                "conversation",
                "programming",
                "reasoning",
                "files",
                "game_dev"
            ],
            "configured_domain_count": domain_count,
            "training": "Each domain is a separate small language model with its own corpus, optimizer run and checkpoint.",
            "composition": "A shared tokenizer and a router choose which expert model to load. Additional specialists can be added without loading all checkpoints into RAM.",
            "relationship_to_dense_target": "This is a feasible modular approximation, not an exact materialization of 40,000 dense layers by 60,000 physical neurons."
        },
        "resource_profiles": practical
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Estimate KLOD target and practical shard sizes")
    parser.add_argument("--out", type=Path, default=Path("config/shard-plan.json"))
    args = parser.parse_args()
    plan = build_plan()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(plan, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
