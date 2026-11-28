import torch
import pytest

from klod.hybrid_model import HybridConfig, HybridKlodModel, SparseDepthRouter
from klod.train_hybrid import estimate_parameters


def micro_config():
    return HybridConfig(
        vocab_size=258,
        hidden_size=64,
        logical_layers=128,
        active_stages=3,
        attention_rank=16,
        attention_heads=4,
        dense_rank=32,
        expert_rank=16,
        stage_rank=16,
        n_experts=4,
        top_k_experts=2,
        max_seq_len=16,
        dropout=0.0,
    )


def test_hybrid_forward_has_expected_shape_and_loss():
    model = HybridKlodModel(micro_config())
    inputs = torch.randint(2, 258, (2, 16))
    targets = torch.randint(2, 258, (2, 16))
    logits, loss = model(inputs, targets)
    assert logits.shape == (2, 16, 258)
    assert loss is not None
    assert torch.isfinite(loss)


def test_hybrid_model_uses_full_dense_and_sparse_components():
    model = HybridKlodModel(micro_config())
    assert model.shared_dense_core is not None
    assert len(model.sparse_experts.experts) == 4
    assert model.sparse_experts.top_k == 2
    assert model.depth_router.logical_layers == 128
    assert model.depth_router.active_stages == 3


def test_hybrid_parameter_estimate_matches_model():
    config = micro_config()
    model = HybridKlodModel(config)
    estimate = estimate_parameters(config)
    assert estimate["total_parameters_estimate"] == model.parameter_count()


def test_depth_router_selects_stages_per_token_without_future_leakage():
    config = micro_config()
    router = SparseDepthRouter(config).eval()
    first = torch.randn(2, 10, config.hidden_size)
    changed_future = first.clone()
    changed_future[:, 6:, :] = torch.randn_like(changed_future[:, 6:, :]) * 5
    ids_a, weights_a, _ = router(first)
    ids_b, weights_b, _ = router(changed_future)
    assert ids_a.shape == (2, 10, config.active_stages)
    assert torch.equal(ids_a[:, :6], ids_b[:, :6])
    assert torch.allclose(weights_a[:, :6], weights_b[:, :6])


def test_hybrid_parameter_estimate_is_positive_and_lower_than_dense_target():
    config = HybridConfig(
        hidden_size=40000,
        logical_layers=20000,
        active_stages=8,
        attention_rank=64,
        dense_rank=128,
        expert_rank=64,
        stage_rank=64,
        n_experts=8,
        top_k_experts=2,
    )
    estimate = estimate_parameters(config)
    dense_equivalent = (config.logical_layers - 1) * config.hidden_size * config.hidden_size
    assert estimate["total_parameters_estimate"] > 0
    assert estimate["total_parameters_estimate"] < dense_equivalent
    assert estimate["fp16_weight_bytes_estimate"] == estimate["total_parameters_estimate"] * 2


def test_hybrid_config_rejects_invalid_top_k():
    config = micro_config()
    config.top_k_experts = config.n_experts + 1
    with pytest.raises(ValueError):
        config.validate()


def test_hybrid_generation_runs():
    model = HybridKlodModel(micro_config()).eval()
    inputs = torch.randint(2, 258, (1, 8))
    generated = model.generate(inputs, max_new_tokens=3)
    assert generated.shape[0] == 1
    assert generated.shape[1] >= 8
