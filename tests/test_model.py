import torch

from deta.model import build_default_model


def test_default_parameter_count_is_near_80000():
    model = build_default_model()
    assert model.parameter_count() == 79_824
    assert abs(model.parameter_count() - 80_000) <= 500


def test_model_forward_shapes():
    model = build_default_model()
    tokens = torch.randint(0, 256, (2, 12), dtype=torch.long)
    logits, state = model(tokens)
    assert logits.shape == (2, 12, 256)
    assert state.shape == (1, 2, 88)
