import hashlib
import os
import random
import tempfile
from pathlib import Path
from typing import Any

import torch
from torch import nn

from deta.config import DetaConfig
from deta.data import read_licensed_jsonl
from deta.model import DetaFiveGroupModel, DetaGroup, build_default_model, build_grouped_model


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


def _corpus_split(corpus: torch.Tensor, sequence_length: int) -> tuple[torch.Tensor, torch.Tensor]:
    minimum_size = 2 * (sequence_length + 2)
    if corpus.numel() < minimum_size:
        raise ValueError(
            f"Approved corpus has {corpus.numel()} bytes; at least {minimum_size} are required."
        )
    split_index = min(
        max(int(corpus.numel() * 0.9), sequence_length + 2),
        corpus.numel() - sequence_length - 2,
    )
    return corpus[:split_index], corpus[split_index:]


def _sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_save(payload: dict[str, Any], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_path = tempfile.mkstemp(
        dir=destination.parent,
        prefix=destination.name + ".",
        suffix=".tmp",
    )
    try:
        with os.fdopen(file_descriptor, "wb") as stream:
            torch.save(payload, stream)
        os.replace(temporary_path, destination)
    finally:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)


def _checkpoint_payload(
    model: DetaFiveGroupModel,
    config: DetaConfig,
    dataset_sha256: str,
    dataset_path: str | Path,
    seed: int,
    max_bytes: int,
    completed_groups: int,
    steps_by_group: dict[str, int],
    metrics_by_group: dict[str, dict[str, float]],
) -> dict[str, Any]:
    return {
        "format_version": 2,
        "model_type": "DetaFiveGroupModel",
        "model_state_dict": model.state_dict(),
        "model_parameters": model.parameter_count(),
        "group_parameters": [model.group_parameter_count(index) for index in range(model.group_count)],
        "config": dict(config.__dict__),
        "groups_completed": completed_groups,
        "training_steps": sum(steps_by_group.values()),
        "steps_by_group": dict(steps_by_group),
        "metrics_by_group": dict(metrics_by_group),
        "seed": seed,
        "dataset_path": str(Path(dataset_path)),
        "dataset_sha256": dataset_sha256,
        "max_bytes": max_bytes,
    }


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
    selected_device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    if selected_device == "cuda" and not torch.cuda.is_available():
        raise ValueError("CUDA was requested but is not available.")
    random.seed(seed)
    torch.manual_seed(seed)
    corpus = load_byte_corpus(data_path, max_bytes=max_bytes).to(selected_device)
    training_corpus, validation_corpus = _corpus_split(corpus, cfg.sequence_length)

    model = build_default_model().to(selected_device)
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

    model.eval()
    with torch.no_grad():
        inputs, targets = _sample_batch(
            validation_corpus,
            cfg.sequence_length,
            cfg.batch_size,
        )
        logits, _ = model(inputs)
        validation_loss = float(
            loss_fn(logits.reshape(-1, cfg.vocab_size), targets.reshape(-1)).detach().cpu()
        )

    destination = Path(output_path)
    file_descriptor, temporary_path = tempfile.mkstemp(
        dir=destination.parent if destination.parent.exists() else Path("."),
        prefix=destination.name + ".",
        suffix=".tmp",
    )
    os.close(file_descriptor)
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        torch.save(
            {
                "model_state_dict": model.state_dict(),
                "model_parameters": model.parameter_count(),
                "config": cfg.__dict__,
                "training_steps": prior_steps + steps,
                "run_steps": steps,
                "seed": seed,
                "last_loss": last_loss,
                "validation_loss": validation_loss,
                "dataset_path": str(Path(data_path)),
            },
            temporary_path,
        )
        os.replace(temporary_path, destination)
    finally:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)
    return {
        "parameters": model.parameter_count(),
        "steps": steps,
        "last_loss": last_loss,
        "validation_loss": validation_loss,
        "device": selected_device,
        "checkpoint": str(destination),
    }


def train_five_groups(
    data_path: str | Path,
    output_dir: str | Path,
    steps_per_group: int = 1000,
    start_group: int = 1,
    end_group: int = 5,
    config: DetaConfig | None = None,
    device: str | None = None,
    resume_from: str | Path | None = None,
    seed: int = 42,
    max_bytes: int = DEFAULT_MAX_TRAINING_BYTES,
) -> dict[str, Any]:
    cfg = config or DetaConfig()
    cfg.validate()
    if steps_per_group < 1:
        raise ValueError("steps_per_group must be positive")
    if seed < 0:
        raise ValueError("seed must be non-negative")
    if not 1 <= start_group <= end_group <= 5:
        raise ValueError("Group range must satisfy 1 <= start_group <= end_group <= 5")
    if start_group == 1 and resume_from is not None:
        raise ValueError("A fresh run starts at group 1 and must not use --resume-from.")
    if start_group > 1 and resume_from is None:
        raise ValueError("Resuming at group 2-5 requires --resume-from with the prior group's checkpoint.")

    selected_device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    if selected_device == "cuda" and not torch.cuda.is_available():
        raise ValueError("CUDA was requested but is not available.")
    data_path = Path(data_path)
    if not data_path.is_file():
        raise FileNotFoundError(f"Dataset manifest does not exist: {data_path}")

    random.seed(seed)
    torch.manual_seed(seed)
    if selected_device == "cuda":
        torch.cuda.manual_seed_all(seed)

    corpus = load_byte_corpus(data_path, max_bytes=max_bytes)
    training_corpus, validation_corpus = _corpus_split(corpus, cfg.sequence_length)
    training_corpus = training_corpus.to(selected_device)
    validation_corpus = validation_corpus.to(selected_device)
    dataset_sha256 = _sha256_file(data_path)
    model = build_grouped_model(cfg).to(selected_device)
    steps_by_group: dict[str, int] = {}
    metrics_by_group: dict[str, dict[str, float]] = {}
    output_directory = Path(output_dir)
    output_directory.mkdir(parents=True, exist_ok=True)

    if resume_from is not None:
        checkpoint_path = Path(resume_from)
        if not checkpoint_path.is_file():
            raise FileNotFoundError(f"Resume checkpoint does not exist: {checkpoint_path}")
        checkpoint = torch.load(checkpoint_path, map_location=selected_device, weights_only=True)
        if not isinstance(checkpoint, dict) or checkpoint.get("model_type") != "DetaFiveGroupModel":
            raise ValueError("Resume checkpoint is not a DetaFiveGroupModel checkpoint.")
        if checkpoint.get("config") != dict(cfg.__dict__):
            raise ValueError("Resume checkpoint architecture/configuration does not match this run.")
        if checkpoint.get("dataset_sha256") != dataset_sha256:
            raise ValueError("Dataset manifest differs from the checkpoint; refusing mixed-data training.")
        if int(checkpoint.get("groups_completed", -1)) != start_group - 1:
            raise ValueError("Resume checkpoint must be from exactly the group before start_group.")
        model.load_state_dict(checkpoint["model_state_dict"], strict=True)
        steps_by_group = dict(checkpoint.get("steps_by_group", {}))
        metrics_by_group = dict(checkpoint.get("metrics_by_group", {}))

    loss_fn = nn.CrossEntropyLoss()
    group_results = []

    for group_number in range(start_group, end_group + 1):
        group_index = group_number - 1
        group: DetaGroup = model.groups[group_index]
        group_seed = seed + group_number * 10_000
        random.seed(group_seed)
        torch.manual_seed(group_seed)
        if selected_device == "cuda":
            torch.cuda.manual_seed_all(group_seed)

        model.eval()
        group.train()
        optimizer = torch.optim.AdamW(group.parameters(), lr=cfg.learning_rate)
        last_loss = 0.0
        for step in range(1, steps_per_group + 1):
            inputs, targets = _sample_batch(
                training_corpus,
                cfg.sequence_length,
                cfg.batch_size,
            )
            optimizer.zero_grad(set_to_none=True)
            logits = model(
                inputs,
                active_groups=group_number,
                train_group=group_index,
            )
            loss = loss_fn(logits.reshape(-1, cfg.vocab_size), targets.reshape(-1))
            if not torch.isfinite(loss):
                raise FloatingPointError(
                    f"Training loss became non-finite in group {group_number}; last checkpoint is preserved."
                )
            loss.backward()
            torch.nn.utils.clip_grad_norm_(group.parameters(), max_norm=1.0)
            optimizer.step()
            last_loss = float(loss.detach().cpu())
            if step == 1 or step % 100 == 0 or step == steps_per_group:
                print(
                    f"[Deta] group={group_number}/5 step={step}/{steps_per_group} loss={last_loss:.5f}",
                    flush=True,
                )

        model.eval()
        random.seed(seed + 1_000_000 + group_number)
        with torch.no_grad():
            inputs, targets = _sample_batch(
                validation_corpus,
                cfg.sequence_length,
                cfg.batch_size,
            )
            logits = model(inputs, active_groups=group_number)
            validation_loss = float(
                loss_fn(logits.reshape(-1, cfg.vocab_size), targets.reshape(-1)).detach().cpu()
            )

        steps_by_group[str(group_number)] = steps_per_group
        metrics_by_group[str(group_number)] = {
            "last_training_loss": last_loss,
            "validation_loss": validation_loss,
        }
        payload = _checkpoint_payload(
            model=model,
            config=cfg,
            dataset_sha256=dataset_sha256,
            dataset_path=data_path,
            seed=seed,
            max_bytes=max_bytes,
            completed_groups=group_number,
            steps_by_group=steps_by_group,
            metrics_by_group=metrics_by_group,
        )
        group_checkpoint = output_directory / f"group-{group_number:02d}.pt"
        _atomic_save(payload, group_checkpoint)
        if group_number == 5:
            _atomic_save(payload, output_directory / "final.pt")

        result = {
            "group": group_number,
            "group_parameters": model.group_parameter_count(group_index),
            "total_parameters": model.parameter_count(),
            "steps": steps_per_group,
            "last_training_loss": last_loss,
            "validation_loss": validation_loss,
            "checkpoint": str(group_checkpoint),
        }
        group_results.append(result)
        print(
            f"[Deta] completed group {group_number}/5; "
            f"validation_loss={validation_loss:.5f}; checkpoint={group_checkpoint}",
            flush=True,
        )

    return {
        "model_type": "DetaFiveGroupModel",
        "total_parameters": model.parameter_count(),
        "target_parameters": cfg.target_parameters,
        "groups_completed": end_group,
        "training_steps_this_run": steps_per_group * len(group_results),
        "training_steps_total": sum(steps_by_group.values()),
        "device": selected_device,
        "seed": seed,
        "dataset_sha256": dataset_sha256,
        "groups": group_results,
        "final_checkpoint": str(output_directory / ("final.pt" if end_group == 5 else f"group-{end_group:02d}.pt")),
    }
