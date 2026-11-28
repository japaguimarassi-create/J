import json
import random
import tempfile
from pathlib import Path

from klod.shard_plan import build_plan, estimate_dense_target, estimate_profile
from klod.shard_runtime import ShardedKlodRuntime


def test_dense_target_estimate_is_consistent():
    target = estimate_dense_target(40000, 60000)
    assert target["virtual_neuron_slots"] == 2_400_000_000
    assert target["dense_weight_parameters_estimate"] == 143_996_400_000_000
    assert target["tiles_per_axis"] == 120
    assert target["total_matrix_tiles_estimate"] == 576_000_000


def test_practical_resource_profiles_are_monotonic():
    profiles = [estimate_profile(name) for name in ("micro", "small", "medium", "large")]
    sizes = [item["estimated_parameters"] for item in profiles]
    assert sizes == sorted(sizes)
    assert all(item["adamw_training_state_floor_bytes"] > item["fp32_weights_bytes"] for item in profiles)


def test_plan_separates_dense_target_from_practical_shards():
    plan = build_plan()
    assert plan["target"]["logical_layers"] == 40000
    assert plan["practical_capability_sharding"]["configured_domain_count"] == 5
    assert "not an exact" in plan["practical_capability_sharding"]["relationship_to_dense_target"]


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
