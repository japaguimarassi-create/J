import random
from pathlib import Path

import torch
from torch import nn

from deta.config import DetaConfig
from deta.data import read_licensed_jsonl
from deta.model import build_default_model


def load_byte_corpus(data_path: str | Path) -> torch.Tensor:
    accepted = [record["content"].encode("utf-8") for record in read_licensed_jsonl(data_path)]
    if not accepted:
        raise ValueError("No eligible, licensed records were found in the dataset manifest.")
    corpus = b"\n".join(accepted)
    if len(corpus) < 4:
        raise ValueError("The approved training corpus is too small.")
    return torch.tensor(list(corpus), dtype=torch.long)


def train_checkpoint(
    data_path: str | Path,
    output_path: str | Path,
    steps: int = 1000,
    config: DetaConfig | None = None,
    device: str | None = None,
) -> dict[str, float | int | str]:
    cfg = config or DetaConfig()
    cfg.validate()
    if steps < 1:
        raise ValueError("steps must be positive")
    selected_device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    corpus = load_byte_corpus(data_path).to(selected_device)
    if corpus.numel() <= cfg.sequence_length + 1:
        raise ValueError(
            f"Approved corpus has {corpus.numel()} bytes; need more than {cfg.sequence_length + 1}."
        )

    model = build_default_model().to(selected_device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=cfg.learning_rate)
    loss_fn = nn.CrossEntropyLoss()
    model.train()
    last_loss = 0.0
    max_start = corpus.numel() - cfg.sequence_length - 1

    for _ in range(steps):
        starts = [random.randrange(max_start + 1) for _ in range(cfg.batch_size)]
        inputs = torch.stack([corpus[start:start + cfg.sequence_length] for start in starts])
        targets = torch.stack([corpus[start + 1:start + cfg.sequence_length + 1] for start in starts])
        optimizer.zero_grad(set_to_none=True)
        logits, _ = model(inputs)
        loss = loss_fn(logits.reshape(-1, 256), targets.reshape(-1))
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        last_loss = float(loss.detach().cpu())

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        "model_state_dict": model.state_dict(),
        "model_parameters": model.parameter_count(),
        "config": cfg.__dict__,
        "training_steps": steps,
        "dataset_path": str(Path(data_path)),
    }, destination)
    return {
        "parameters": model.parameter_count(),
        "steps": steps,
        "last_loss": last_loss,
        "device": selected_device,
        "checkpoint": str(destination),
    }
