import argparse
import json
from pathlib import Path


TARGET_LAYERS = 20000
TARGET_WIDTH = 40000
TILE_WIDTH = 500
VOCAB_SIZE = 258


PROFILES = {
    "micro": {"layers": 1, "width": 32, "heads": 2, "experts": 2, "seq_len": 64},
    "small": {"layers": 2, "width": 64, "heads": 4, "experts": 2, "seq_len": 128},
    "medium": {"layers": 4, "width": 128, "heads": 4, "experts": 4, "seq_len": 256},
    "large": {"layers": 6, "width": 256, "heads": 8, "experts": 4, "seq_len": 512},
}


def estimate_dense_target(
    layers: int = TARGET_LAYERS,
    width: int = TARGET_WIDTH,
    tile_width: int = TILE_WIDTH,
) -> dict:
    if layers < 1 or width < 1 or tile_width < 1:
        raise ValueError("layers, width and tile_width must be positive")
    parameters = max(0, layers - 1) * width * width
    fp16_bytes = parameters * 2
    tiles_per_axis = (width + tile_width - 1) // tile_width
    matrix_tiles = max(0, layers - 1) * tiles_per_axis * tiles_per_axis
    return {
        "logical_layers": layers,
        "virtual_neurons_per_layer": width,
        "virtual_neuron_slots": layers * width,
        "dense_weight_parameters_estimate": parameters,
        "fp16_weight_bytes_estimate": fp16_bytes,
        "fp16_weight_decimal_tb_estimate": fp16_bytes / 1_000_000_000_000,
        "fp16_weight_binary_tib_estimate": fp16_bytes / (1024 ** 4),
        "tile_width": tile_width,
        "tiles_per_axis": tiles_per_axis,
        "matrix_tiles_per_transition": tiles_per_axis * tiles_per_axis,
        "total_matrix_tiles_estimate": matrix_tiles,
        "weights_per_full_tile": tile_width * tile_width,
        "fp16_bytes_per_full_tile": tile_width * tile_width * 2,
        "warning": "Dense matrix tiles are a storage decomposition only. Faithful training still requires coordinated forward activations and end-to-end gradients."
    }


def estimate_hybrid_target(
    hidden_size: int = 40000,
    logical_layers: int = 20000,
    active_stages: int = 8,
    attention_rank: int = 64,
    dense_rank: int = 128,
    expert_rank: int = 64,
    stage_rank: int = 64,
    n_experts: int = 8,
    vocab_size: int = VOCAB_SIZE,
    max_seq_len: int = 256,
) -> dict:
    if min(hidden_size, logical_layers, active_stages, attention_rank, dense_rank, expert_rank, stage_rank, n_experts) < 1:
        raise ValueError("All architecture dimensions must be positive")
    if active_stages > logical_layers:
        raise ValueError("active_stages cannot exceed logical_layers")

    h = hidden_size
    a = attention_rank
    d = dense_rank
    e = expert_rank
    s = stage_rank
    stages = logical_layers
    components = {
        "token_embedding": vocab_size * h,
        "position_embedding_and_projection": max_seq_len * s + s * h,
        "logical_stage_router": h * s + s + s * stages + stages,
        "logical_stage_embeddings": stages * s + s * h,
        "factorized_attention": 4 * h * a + 4 * a * a + 4 * a,
        "shared_dense_core": 2 * h * d,
        "sparse_low_rank_experts": 2 * n_experts * h * e,
        "expert_router": h * n_experts + n_experts,
        "sparse_gate": h + 1,
        "normalization": 6 * h,
        "language_model_head": h * a + a * vocab_size,
    }
    hybrid_parameters = sum(components.values())
    dense_parameters = max(0, logical_layers - 1) * hidden_size * hidden_size
    hybrid_fp16_bytes = hybrid_parameters * 2
    dense_fp16_bytes = dense_parameters * 2
    return {
        "hybrid_design": {
            "logical_layers": logical_layers,
            "virtual_neurons_per_layer": hidden_size,
            "active_stages_per_forward": active_stages,
            "stage_selection": "learned top-k from the logical stage bank",
            "dense_path": "shared low-rank dense transformation applied to every token at each active stage",
            "sparse_path": "top-k low-rank experts selected per token",
            "weight_sharing": "the dense core and expert bank are reused across selected logical stages"
        },
        "component_parameter_estimates": components,
        "hybrid_parameter_count_estimate": hybrid_parameters,
        "hybrid_fp16_weight_bytes_estimate": hybrid_fp16_bytes,
        "hybrid_fp16_weight_decimal_gb_estimate": hybrid_fp16_bytes / 1_000_000_000,
        "hybrid_adamw_state_floor_bytes_estimate": hybrid_parameters * 16,
        "dense_equivalent_parameter_estimate": dense_parameters,
        "dense_equivalent_fp16_weight_decimal_tb_estimate": dense_fp16_bytes / 1_000_000_000_000,
        "parameter_reduction_factor_estimate": dense_parameters / max(1, hybrid_parameters),
        "warning": "The hybrid model has 40,000-wide hidden states and a 20,000-stage logical bank, but only active_stages are executed per forward. The dense transformation is factorized and shared; this is not the same function as a fully dense, unshared 20,000-layer network. Estimates exclude activations, gradients and runtime workspaces."
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
        "note": "Compact expert profile estimate. Activations and workspaces require more memory."
    }


def build_plan(domain_count: int = 5) -> dict:
    if domain_count < 1:
        raise ValueError("domain_count must be positive")
    target = estimate_dense_target()
    hybrid = estimate_hybrid_target()
    practical = {name: estimate_profile(name) for name in PROFILES}
    return {
        "name": "KLOD 20k x 40k hybrid dense-sparse plan",
        "target": target,
        "hybrid": hybrid,
        "literal_tensor_sharding": {
            "neuron_tile_width": TILE_WIDTH,
            "tiles_per_neuron_axis": target["tiles_per_axis"],
            "tiles_per_dense_layer_transition": target["matrix_tiles_per_transition"],
            "total_weight_tiles": target["total_matrix_tiles_estimate"],
            "trainability": "A tile can be stored separately, but faithful training requires end-to-end gradients across the full network."
        },
        "practical_capability_sharding": {
            "default_domains": ["conversation", "programming", "reasoning", "files", "game_dev"],
            "configured_domain_count": domain_count,
            "relationship_to_target": "Specialist checkpoints complement the hybrid model. They are not a dense-network substitute."
        },
        "resource_profiles": practical
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Estimate KLOD dense target and hybrid dense-sparse resources")
    parser.add_argument("--out", type=Path, default=Path("config/shard-plan.json"))
    args = parser.parse_args()
    plan = build_plan()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(plan, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
