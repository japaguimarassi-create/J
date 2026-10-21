import os
import random
import tempfile
from pathlib import Path

import torch
from torch import nn

from deta.config import DetaConfig
from deta.data import read_licensed_jsonl
from deta.model import DetaByteGRU


DEFAULT_MAX_TRAINING_BYTES = 64 * 1024 * 1024


def load_byte_corpus(
    data_path: str | Path,
    max_bytes: int = DEFAULT_MAX_TRAINING_BYTES,
) -> torch.Tensor:
    if max_bytes < 1:
        raise ValueError("max_bytes must be positive")
    corpus = bytearray()
    for record in read_licensed_jsonl(data_path):
        remaining = max_bytes - len(corpus)
        if remaining <= 0:
            break
        encoded = record["content"].encode("utf-8")
        corpus.extend(encoded[:remaining])
        if len(corpus) < max_bytes:
            corpus.extend(b"\n"[:max_bytes - len(corpus)])
    if len(corpus) < 4:
        raise ValueError("No eligible, licensed records with enough content were found.")
    return torch.tensor(list(corpus), dtype=torch.long)


def _sample_batch(
    corpus: torch.Tensor,
    sequence_length: int,
    batch_size: int,
) -> tuple[torch.Tensor, torch.Tensor]:
    max_start = corpus.numel() - sequence_length - 1
    if max_start < 0:
        raise ValueError("Corpus segment is shorter than the configured sequence length.")
    starts = [random.randrange(max_start + 1) for _ in range(batch_size)]
    inputs = torch.stack([corpus[start:start + sequence_length] for start in starts])
    targets = torch.stack(
        [corpus[start + 1:start + sequence_length + 1] for start in starts]
    )
    return inputs, targets


def _evaluate(
    model: DetaByteGRU,
    corpus: torch.Tensor,
    cfg: DetaConfig,
    loss_fn: nn.Module,
) -> float:
    model.eval()
    with torch.no_grad():
        inputs, targets = _sample_batch(corpus, cfg.sequence_length, cfg.batch_size)
        logits, _ = model(inputs)
        loss = loss_fn(logits.reshape(-1, cfg.vocab_size), targets.reshape(-1))
    return float(loss.detach().cpu())


def train_checkpoint(
    data_path: str | Path,
    output_path: str | Path,
    steps: int = 1000,
    config: DetaConfig | None = None,
    device: str | None = None,
    resume_from: str | Path | None = None,
    seed: int = 42,
    max_bytes: int = DEFAULT_MAX_TRAINING_BYTES,
) -> dict[str, float | int | str]:
    cfg = config or DetaConfig()
    cfg.validate()
    if steps < 1:
        raise ValueError("steps must be positive")
    if seed < 0:
        raise ValueError("seed must be non-negative")
    selected_device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    if selected_device == "cuda" and not torch.cuda.is_available():
        raise ValueError("CUDA was requested but is not available.")
    random.seed(seed)
    torch.manual_seed(seed)
    if selected_device == "cuda":
        torch.cuda.manual_seed_all(seed)

    corpus = load_byte_corpus(data_path, max_bytes=max_bytes)
    minimum_size = 2 * (cfg.sequence_length + 2)
    if corpus.numel() < minimum_size:
        raise ValueError(
            f"Approved corpus has {corpus.numel()} bytes; at least {minimum_size} are required."
        )

    split_index = min(max(int(corpus.numel() * 0.9), cfg.sequence_length + 2), corpus.numel() - cfg.sequence_length - 2)
    training_corpus = corpus[:split_index].to(selected_device)
    validation_corpus = corpus[split_index:].to(selected_device)

    model = DetaByteGRU(
        vocab_size=cfg.vocab_size,
        embedding_dim=cfg.embedding_dim,
        hidden_dim=cfg.hidden_dim,
    ).to(selected_device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=cfg.learning_rate)
    loss_fn = nn.CrossEntropyLoss()
    prior_steps = 0

    if resume_from is not None:
        checkpoint_path = Path(resume_from)
        if not checkpoint_path.is_file():
            raise FileNotFoundError(f"Resume checkpoint does not exist: {checkpoint_path}")
        checkpoint = torch.load(checkpoint_path, map_location=selected_device, weights_only=True)
        if not isinstance(checkpoint, dict) or not isinstance(checkpoint.get("model_state_dict"), dict):
            raise ValueError("Checkpoint is invalid or has no model_state_dict.")
        model.load_state_dict(checkpoint["model_state_dict"], strict=True)
        optimizer_state = checkpoint.get("optimizer_state_dict")
        if isinstance(optimizer_state, dict):
            optimizer.load_state_dict(optimizer_state)
        prior_steps = int(checkpoint.get("training_steps", 0))
        if prior_steps < 0:
            raise ValueError("Checkpoint contains an invalid training step count.")

    model.train()
    last_loss = 0.0
    for _ in range(steps):
        inputs, targets = _sample_batch(
            training_corpus,
            cfg.sequence_length,
            cfg.batch_size,
        )
        optimizer.zero_grad(set_to_none=True)
        logits, _ = model(inputs)
        loss = loss_fn(logits.reshape(-1, cfg.vocab_size), targets.reshape(-1))
        if not torch.isfinite(loss):
            raise FloatingPointError("Training loss became non-finite; checkpoint was not written.")
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        last_loss = float(loss.detach().cpu())

    validation_loss = _evaluate(model, validation_corpus, cfg, loss_fn)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_path = tempfile.mkstemp(
        dir=destination.parent,
        prefix=destination.name + ".",
        suffix=".tmp",
    )
    os.close(file_descriptor)
    try:
        torch.save(
            {
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "model_parameters": model.parameter_count(),
                "config": cfg.__dict__,
                "training_steps": prior_steps + steps,
                "run_steps": steps,
                "seed": seed,
                "last_training_loss": last_loss,
                "validation_loss": validation_loss,
                "dataset_path": str(Path(data_path)),
                "max_bytes": max_bytes,
            },
            temporary_path,
        )
        os.replace(temporary_path, destination)
    finally:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)

    return {
        "parameters": model.parameter_count(),
        "steps_this_run": steps,
        "total_training_steps": prior_steps + steps,
        "last_training_loss": last_loss,
        "validation_loss": validation_loss,
        "device": selected_device,
        "seed": seed,
        "checkpoint": str(destination),
    }
