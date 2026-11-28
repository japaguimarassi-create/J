import json
import tempfile
from pathlib import Path

from klod.shard_plan import build_plan, estimate_dense_target, estimate_hybrid_target, estimate_profile
from klod.shard_runtime import ShardedKlodRuntime


def test_dense_target_estimate_is_consistent():
    target = estimate_dense_target(20000, 40000)
    assert target["virtual_neuron_slots"] == 800_000_000
    assert target["dense_weight_parameters_estimate"] == 31_998_400_000_000
    assert target["fp16_weight_decimal_tb_estimate"] == 63.9968
    assert target["tiles_per_axis"] == 80
    assert target["matrix_tiles_per_transition"] == 6400
    assert target["total_matrix_tiles_estimate"] == 127_993_600


def test_hybrid_estimate_uses_shared_dense_and_sparse_paths():
    result = estimate_hybrid_target()
    assert result["hybrid_design"]["logical_layers"] == 20000
    assert result["hybrid_design"]["virtual_neurons_per_layer"] == 40000
    assert result["hybrid_design"]["active_stages_per_forward"] == 8
    assert result["hybrid_parameter_count_estimate"] < result["dense_equivalent_parameter_estimate"]
    assert result["parameter_reduction_factor_estimate"] > 100


def test_practical_resource_profiles_are_monotonic():
    profiles = [estimate_profile(name) for name in ("micro", "small", "medium", "large")]
    sizes = [item["estimated_parameters"] for item in profiles]
    assert sizes == sorted(sizes)
    assert all(item["adamw_training_state_floor_bytes"] > item["fp32_weights_bytes"] for item in profiles)


def test_plan_separates_dense_target_and_hybrid_approximation():
    plan = build_plan()
    assert plan["target"]["logical_layers"] == 20000
    assert plan["target"]["virtual_neurons_per_layer"] == 40000
    assert plan["practical_capability_sharding"]["default_domains"] == [
        "conversation", "programming", "reasoning", "files", "game_dev"
    ]
    assert "not the same function" in plan["hybrid"]["warning"]


def test_router_selects_relevant_shard_and_falls_back():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        manifest = root / "config" / "shards.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({
            "default_shard": "conversation",
            "shards": [
                {"id":"conversation","domain":"chat","keywords":["olá","conversa"]},
                {"id":"programming","domain":"code","keywords":["python","código","codigo"]},
            ]
        }), encoding="utf-8")
        runtime = ShardedKlodRuntime(manifest, root / "runs")
        assert runtime.route("Preciso de código Python") == "programming"
        assert runtime.route("Olá, tudo bem?") == "conversation"
        assert runtime.route("pedido sem palavra-chave") == "conversation"
