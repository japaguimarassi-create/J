from klod.evolution import GrowthPolicy
from klod.neural import ModelConfig


def test_growth_policy_proposes_a_larger_model_after_milestone():
    policy = GrowthPolicy(interval_steps=100, max_parameters=2_000_000)
    current = ModelConfig(vocab_size=512, max_seq_len=128, d_model=32, n_heads=4, n_layers=2, d_ff=64)
    decision = policy.propose(current, 500, 300, 1.0, 1.01)
    assert decision.approved
    assert decision.target_config is not None
    assert decision.target_config.n_layers == 3
    assert decision.target_config.d_ff >= 64
    assert decision.target_config.max_seq_len == 256


def test_growth_policy_rejects_bad_validation_and_too_early_growth():
    policy = GrowthPolicy(interval_steps=100)
    current = ModelConfig(vocab_size=512, max_seq_len=128, d_model=32, n_heads=4, n_layers=2, d_ff=64)
    early = policy.propose(current, 350, 300, 1.0, 0.9)
    bad_quality = policy.propose(current, 500, 300, 1.0, 1.5)
    assert not early.approved
    assert not bad_quality.approved


def test_growth_policy_enforces_parameter_budget():
    policy = GrowthPolicy(interval_steps=10, max_parameters=1000)
    current = ModelConfig(vocab_size=512, max_seq_len=128, d_model=32, n_heads=4, n_layers=2, d_ff=64)
    decision = policy.propose(current, 100, 0, 1.0, 1.0)
    assert not decision.approved
    assert "budget" in decision.reason
