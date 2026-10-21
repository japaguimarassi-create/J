import pytest
import torch

from deta.model import DetaFiveGroupModel, build_default_model, build_grouped_model


def test_original_baseline_parameter_count_is_preserved():
    model = build_default_model()
    assert model.parameter_count() == 79_824


def test_grouped_model_has_exactly_400000_trainable_parameters():
    model = build_grouped_model()
    assert model.parameter_count() == 400_000
    assert [model.group_parameter_count(index) for index in range(5)] == [80_000] * 5


def test_each_group_produces_byte_logits():
    model = DetaFiveGroupModel()
    tokens = torch.randint(0, 256, (2, 12), dtype=torch.long)
    logits = model(tokens, active_groups=1)
    assert logits.shape == (2, 12, 256)


def test_incremental_forward_adds_only_active_groups():
    model = DetaFiveGroupModel()
    tokens = torch.randint(0, 256, (2, 7), dtype=torch.long)
    first = model(tokens, active_groups=1)
    combined = model(tokens, active_groups=2)
    second = model.groups[1](tokens)
    assert torch.allclose(combined, first + second)


@pytest.mark.parametrize("active", [0, 6])
def test_invalid_active_group_count_is_rejected(active):
    model = DetaFiveGroupModel()
    tokens = torch.zeros((1, 2), dtype=torch.long)
    with pytest.raises(ValueError, match="active_groups"):
        model(tokens, active_groups=active)


def test_invalid_train_group_is_rejected():
    model = DetaFiveGroupModel()
    tokens = torch.zeros((1, 2), dtype=torch.long)
    with pytest.raises(ValueError, match="train_group"):
        model(tokens, active_groups=2, train_group=2)
