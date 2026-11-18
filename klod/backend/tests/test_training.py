from argparse import Namespace
from pathlib import Path

import torch

from klod.training.train import train


def test_one_real_optimization_run_creates_resumable_checkpoints(tmp_path: Path) -> None:
    dataset = tmp_path / "tiny.txt"
    dataset.write_text(("klod aprende prevendo o próximo token. " * 30) + "fim", encoding="utf-8")
    output_dir = tmp_path / "artifacts"
    args = Namespace(
        dataset=str(dataset), output_dir=str(output_dir), tokenizer=None, retrain_tokenizer=False,
        vocab_size=256, min_frequency=2, seq_len=8, batch_size=1, d_model=16, n_heads=2,
        n_layers=1, d_ff=32, device="cpu", resume=None, learning_rate=1e-3, weight_decay=0.0,
        seed=7, warmup_steps=1, val_fraction=0.1, eval_every=1, eval_batches=1, steps=2,
        gradient_clip=1.0, log_every=1, checkpoint_every=1,
    )
    train(args)
    checkpoint = torch.load(output_dir / "checkpoints" / "latest.pt", map_location="cpu", weights_only=False)
    assert checkpoint["training_steps"] == 2
    assert checkpoint["parameter_count"] > 0
    assert checkpoint["validation_loss"] is not None
    assert (output_dir / "tokenizer.json").is_file()
    assert (output_dir / "checkpoints" / "step-00000002.pt").is_file()
