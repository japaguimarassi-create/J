import json

import torch

from deta.config import DetaConfig
from deta.model import build_grouped_model
from scripts.export_android_model import export_checkpoint


def test_export_checkpoint_writes_valid_android_weights_and_metadata(tmp_path):
    config = DetaConfig()
    model = build_grouped_model(config)
    checkpoint = tmp_path / "final.pt"
    torch.save(
        {
            "model_type": "DetaFiveGroupModel",
            "model_state_dict": model.state_dict(),
            "model_parameters": model.parameter_count(),
            "config": dict(config.__dict__),
            "groups_completed": 5,
            "training_steps": 25000,
            "cumulative_training_steps": 30000,
            "dataset_sha256": "dataset-test",
            "training_lineage": {"parent_checkpoint_sha256": "parent-test"},
            "metrics_by_group": {
                str(index): {"validation_loss": 2.5 - index / 100}
                for index in range(1, 6)
            },
        },
        checkpoint,
    )
    weights = tmp_path / "assets" / "deta-400k.weights"
    metadata_path = tmp_path / "assets" / "deta-model-info.json"

    metadata = export_checkpoint(checkpoint, weights, metadata_path)

    assert weights.stat().st_size == 8 + 400_000 * 4
    assert weights.read_bytes()[:8] == b"DTA400K1"
    saved = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert saved["parameter_count"] == 400_000
    assert saved["groups_completed"] == 5
    assert saved["cumulative_training_steps"] == 30_000
    assert saved["validation_losses"]["1"] == 2.49
    assert metadata["weights_sha256"] == saved["weights_sha256"]
