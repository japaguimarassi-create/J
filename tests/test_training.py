import json

import torch

from deta.config import DetaConfig
from deta.training import load_byte_corpus, train_checkpoint, train_five_groups


def create_manifest(path):
    content = "def square(value):\n    return value * value\n" * 80
    record = {
        "content": content,
        "source_url": "https://github.com/example/repo/blob/main/example.py",
        "license_id": "MIT",
        "source_type": "code",
        "source_name": "example/repo",
        "path": "example.py",
    }
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")


def small_config():
    return DetaConfig(
        embedding_dim=8,
        hidden_dim=8,
        sequence_length=16,
        batch_size=2,
        learning_rate=1e-3,
    )


def test_training_corpus_respects_byte_limit(tmp_path):
    manifest = tmp_path / "approved.jsonl"
    create_manifest(manifest)
    corpus = load_byte_corpus(manifest, max_bytes=128)
    assert corpus.dtype == torch.long
    assert corpus.numel() <= 128


def test_baseline_training_checkpoint_can_resume(tmp_path):
    manifest = tmp_path / "approved.jsonl"
    create_manifest(manifest)
    checkpoint = tmp_path / "baseline.pt"
    first = train_checkpoint(
        data_path=manifest,
        output_path=checkpoint,
        steps=2,
        config=small_config(),
        seed=123,
        max_bytes=4096,
        device="cpu",
    )
    second = train_checkpoint(
        data_path=manifest,
        output_path=checkpoint,
        steps=1,
        config=small_config(),
        resume_from=checkpoint,
        seed=123,
        max_bytes=4096,
        device="cpu",
    )
    assert first["training_steps"] == 2
    assert second["steps"] == 1
    assert second["parameters"] == 79_824
    saved = torch.load(checkpoint, map_location="cpu", weights_only=True)
    assert saved["training_steps"] == 3
    assert saved["validation_loss"] >= 0


def test_five_groups_train_sequentially_and_checkpoint_each_stage(tmp_path):
    manifest = tmp_path / "approved.jsonl"
    create_manifest(manifest)
    output_dir = tmp_path / "checkpoints"
    config = small_config()

    first_run = train_five_groups(
        data_path=manifest,
        output_dir=output_dir,
        steps_per_group=1,
        start_group=1,
        end_group=2,
        config=config,
        seed=123,
        max_bytes=4096,
        device="cpu",
    )

    group_one = torch.load(output_dir / "group-01.pt", map_location="cpu", weights_only=True)
    group_two = torch.load(output_dir / "group-02.pt", map_location="cpu", weights_only=True)

    assert first_run["groups_completed"] == 2
    assert (output_dir / "group-01.pt").is_file()
    assert (output_dir / "group-02.pt").is_file()
    assert group_one["groups_completed"] == 1
    assert group_two["groups_completed"] == 2

    for key, value in group_one["model_state_dict"].items():
        if key.startswith("groups.0."):
            assert torch.equal(value, group_two["model_state_dict"][key])

    assert any(
        not torch.equal(value, group_two["model_state_dict"][key])
        for key, value in group_one["model_state_dict"].items()
        if key.startswith("groups.1.")
    )

    second_run = train_five_groups(
        data_path=manifest,
        output_dir=output_dir,
        steps_per_group=1,
        start_group=3,
        end_group=5,
        config=config,
        resume_from=output_dir / "group-02.pt",
        seed=123,
        max_bytes=4096,
        device="cpu",
    )

    assert second_run["groups_completed"] == 5
    assert second_run["training_steps_total"] == 5
    assert second_run["final_checkpoint"] == str(output_dir / "final.pt")
    final = torch.load(output_dir / "final.pt", map_location="cpu", weights_only=True)
    assert final["groups_completed"] == 5
    assert len(final["group_parameters"]) == 5
    assert (output_dir / "group-05.pt").is_file()


def test_group_training_rejects_a_changed_manifest_on_resume(tmp_path):
    manifest = tmp_path / "approved.jsonl"
    create_manifest(manifest)
    output_dir = tmp_path / "checkpoints"
    train_five_groups(
        data_path=manifest,
        output_dir=output_dir,
        steps_per_group=1,
        start_group=1,
        end_group=1,
        config=small_config(),
        max_bytes=4096,
        device="cpu",
    )

    changed = json.loads(manifest.read_text(encoding="utf-8"))
    changed["content"] += "# changed\n"
    manifest.write_text(json.dumps(changed) + "\n", encoding="utf-8")

    try:
        train_five_groups(
            data_path=manifest,
            output_dir=output_dir,
            steps_per_group=1,
            start_group=2,
            end_group=2,
            config=small_config(),
            resume_from=output_dir / "group-01.pt",
            max_bytes=4096,
            device="cpu",
        )
        assert False, "Expected dataset digest validation to reject changed data"
    except ValueError as exc:
        assert "Dataset manifest differs" in str(exc)

def test_warm_start_preserves_previous_weights_and_tracks_new_dataset(tmp_path):
    manifest = tmp_path / "approved.jsonl"
    create_manifest(manifest)
    old_output = tmp_path / "old-checkpoints"
    config = small_config()

    train_five_groups(
        data_path=manifest,
        output_dir=old_output,
        steps_per_group=1,
        start_group=1,
        end_group=5,
        config=config,
        seed=123,
        max_bytes=4096,
        device="cpu",
    )
    old_checkpoint = torch.load(old_output / "final.pt", map_location="cpu", weights_only=True)
    old_hash = old_checkpoint["dataset_sha256"]
    old_steps = old_checkpoint["training_steps"]

    record = json.loads(manifest.read_text(encoding="utf-8"))
    record["content"] += "\n# additional approved training sample\n"
    manifest.write_text(json.dumps(record) + "\n", encoding="utf-8")

    new_output = tmp_path / "continued-checkpoints"
    result = train_five_groups(
        data_path=manifest,
        output_dir=new_output,
        steps_per_group=1,
        start_group=1,
        end_group=5,
        config=config,
        initial_weights=old_output / "final.pt",
        seed=123,
        max_bytes=4096,
        device="cpu",
    )
    new_checkpoint = torch.load(new_output / "final.pt", map_location="cpu", weights_only=True)

    assert result["training_lineage"]["warm_start"] is True
    assert result["training_lineage"]["parent_training_steps"] == old_steps
    assert result["training_lineage"]["parent_dataset_sha256"] == old_hash
    assert new_checkpoint["dataset_sha256"] != old_hash
    assert new_checkpoint["groups_completed"] == 5
    assert new_checkpoint["training_lineage"]["parent_checkpoint_sha256"]

