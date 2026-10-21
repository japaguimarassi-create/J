import pytest
import torch

from deta.config import DetaConfig
from deta.inference import generate_completion
from deta.model import build_grouped_model


def make_checkpoint(path):
    config = DetaConfig(
        embedding_dim=8,
        hidden_dim=8,
        sequence_length=16,
        batch_size=2,
    )
    model = build_grouped_model(config)
    torch.save(
        {
            "model_type": "DetaFiveGroupModel",
            "model_state_dict": model.state_dict(),
            "config": dict(config.__dict__),
            "groups_completed": 5,
            "training_steps": 5,
        },
        path,
    )


def test_local_completion_loads_checkpoint_and_returns_generated_bytes(tmp_path):
    checkpoint = tmp_path / "model.pt"
    make_checkpoint(checkpoint)
    result = generate_completion(
        checkpoint_path=checkpoint,
        prompt="def add(a, b):",
        max_new_tokens=8,
        temperature=0.8,
        top_k=1,
        seed=7,
        device="cpu",
    )
    assert result["parameters"] > 0
    assert result["groups_used"] == 5
    assert result["new_tokens"] == 8
    assert isinstance(result["completion"], str)
    assert result["mode"].startswith("local byte-level")


def test_local_completion_rejects_invalid_limits(tmp_path):
    checkpoint = tmp_path / "model.pt"
    make_checkpoint(checkpoint)
    with pytest.raises(ValueError, match="max_new_tokens"):
        generate_completion(checkpoint, "x", max_new_tokens=0, device="cpu")
    with pytest.raises(ValueError, match="temperature"):
        generate_completion(checkpoint, "x", temperature=0, device="cpu")


def test_local_completion_requires_grouped_model_checkpoint(tmp_path):
    checkpoint = tmp_path / "wrong.pt"
    torch.save({"model_state_dict": {}}, checkpoint)
    with pytest.raises(ValueError, match="DetaFiveGroupModel"):
        generate_completion(checkpoint, "x", device="cpu")
