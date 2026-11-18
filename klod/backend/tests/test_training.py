from argparse import Namespace
from pathlib import Path

import torch

from klod.api.runtime import ModelRuntime
from klod.training.train import train


def _args(dataset: Path, output_dir: Path, **overrides):
    values = {
        "dataset": str(dataset),
        "output_dir": str(output_dir),
        "tokenizer": None,
        "retrain_tokenizer": False,
        "expand_tokenizer": False,
        "expand_from": None,
        "vocab_size": 280,
        "min_frequency": 2,
        "max_token_bytes": 128,
        "seq_len": 8,
        "batch_size": 1,
        "d_model": 16,
        "n_heads": 2,
        "n_layers": 1,
        "d_ff": 32,
        "device": "cpu",
        "resume": None,
        "learning_rate": 1e-3,
        "weight_decay": 0.0,
        "seed": 7,
        "warmup_steps": 1,
        "val_fraction": 0.1,
        "eval_every": 1,
        "eval_batches": 1,
        "steps": 2,
        "gradient_clip": 1.0,
        "log_every": 1,
        "checkpoint_every": 1,
    }
    values.update(overrides)
    return Namespace(**values)


def test_training_checkpoint_loads_for_real_inference(tmp_path: Path, monkeypatch) -> None:
    dataset = tmp_path / "tiny.txt"
    dataset.write_text(("klod aprende prevendo o próximo token. " * 30) + "fim", encoding="utf-8")
    output_dir = tmp_path / "artifacts"
    train(_args(dataset, output_dir))
    checkpoint_path = output_dir / "checkpoints" / "latest.pt"
    tokenizer_path = output_dir / "tokenizer.json"
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    assert checkpoint["training_steps"] == 2
    assert checkpoint["parameter_count"] > 0
    assert checkpoint["validation_loss"] is not None
    assert (output_dir / "checkpoints" / "step-00000002.pt").is_file()

    monkeypatch.setenv("KLOD_CHECKPOINT_PATH", str(checkpoint_path))
    monkeypatch.setenv("KLOD_TOKENIZER_PATH", str(tokenizer_path))
    runtime = ModelRuntime()
    runtime.load()
    generated = runtime.generate("Klod", max_new_tokens=1, temperature=1.0)
    assert runtime.training_steps == 2
    assert runtime.parameter_count == checkpoint["parameter_count"]
    assert isinstance(generated, str)


def test_tokenizer_and_neural_model_expand_from_parent_checkpoint(tmp_path: Path) -> None:
    dataset = tmp_path / "train.txt"
    dataset.write_text(("Klod aprende linguagem e código. " * 35) + "fim", encoding="utf-8")
    output_dir = tmp_path / "model"
    train(_args(dataset, output_dir))
    parent = output_dir / "checkpoints" / "latest.pt"
    old = torch.load(parent, map_location="cpu", weights_only=False)

    dataset.write_text(("Klod aprende linguagem e código. " * 35) + ("日本語 العربية punctuation / [] {} " * 8), encoding="utf-8")
    expanded_dir = tmp_path / "expanded"
    train(_args(
        dataset,
        expanded_dir,
        tokenizer=str(output_dir / "tokenizer.json"),
        output_dir=str(expanded_dir),
        expand_tokenizer=True,
        expand_from=str(parent),
        vocab_size=360,
        steps=4,
        n_layers=2,
        d_ff=48,
    ))
    expanded = torch.load(expanded_dir / "checkpoints" / "latest.pt", map_location="cpu", weights_only=False)
    assert expanded["training_steps"] == 4
    assert expanded["parent_checkpoint"] == str(parent)
    assert expanded["parameter_count"] > old["parameter_count"]
    assert expanded["tokenizer_vocab_size"] >= old["tokenizer_vocab_size"]
    assert expanded["expansion"]["added_layers"] == 1
