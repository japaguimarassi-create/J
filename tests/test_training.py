import json

import torch

from deta.config import DetaConfig
from deta.training import load_byte_corpus, train_checkpoint


def create_manifest(path):
    content = "def square(value):\n    return value * value\n" * 40
    record = {
        "content": content,
        "source_url": "https://github.com/example/repo/blob/main/example.py",
        "license_id": "MIT",
        "source_type": "code",
        "source_name": "example/repo",
        "path": "example.py",
    }
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")


def test_training_corpus_respects_byte_limit(tmp_path):
    manifest = tmp_path / "approved.jsonl"
    create_manifest(manifest)
    corpus = load_byte_corpus(manifest, max_bytes=128)
    assert corpus.dtype == torch.long
    assert corpus.numel() <= 128


def test_training_checkpoint_can_resume_incrementally(tmp_path):
    manifest = tmp_path / "approved.jsonl"
    create_manifest(manifest)
    checkpoint = tmp_path / "model.pt"
    config = DetaConfig(
        embedding_dim=8,
        hidden_dim=8,
        sequence_length=16,
        batch_size=2,
        learning_rate=1e-3,
    )

    first = train_checkpoint(
        data_path=manifest,
        output_path=checkpoint,
        steps=2,
        config=config,
        seed=123,
        max_bytes=4096,
        device="cpu",
    )
    second = train_checkpoint(
        data_path=manifest,
        output_path=checkpoint,
        steps=1,
        config=config,
        resume_from=checkpoint,
        seed=123,
        max_bytes=4096,
        device="cpu",
    )

    assert first["total_training_steps"] == 2
    assert second["steps_this_run"] == 1
    assert second["total_training_steps"] == 3
    assert second["parameters"] > 0
    saved = torch.load(checkpoint, map_location="cpu", weights_only=True)
    assert saved["training_steps"] == 3
    assert saved["validation_loss"] >= 0
