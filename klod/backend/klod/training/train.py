from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
from typing import Any

import torch
from torch.utils.data import DataLoader, Dataset

from klod.neural import GPTModel, ModelConfig
from klod.tokenizer import BytePairTokenizer


class TokenWindowDataset(Dataset[torch.Tensor]):
    def __init__(self, token_ids: list[int], sequence_length: int) -> None:
        if len(token_ids) <= sequence_length:
            raise ValueError("Corpus must contain more tokens than --seq-len")
        self.tokens = torch.tensor(token_ids, dtype=torch.long)
        self.sequence_length = sequence_length

    def __len__(self) -> int:
        return self.tokens.numel() - self.sequence_length

    def __getitem__(self, index: int) -> torch.Tensor:
        return self.tokens[index:index + self.sequence_length + 1]


def read_corpus(path: Path) -> list[str]:
    texts: list[str] = []
    with path.open("r", encoding="utf-8") as stream:
        for line_number, raw_line in enumerate(stream, start=1):
            line = raw_line.rstrip("\n")
            if not line:
                continue
            if path.suffix.lower() == ".jsonl":
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as error:
                    raise ValueError(f"Invalid JSONL at line {line_number}: {error}") from error
                text = record.get("text") if isinstance(record, dict) else None
                if not isinstance(text, str):
                    raise ValueError(f"JSONL line {line_number} must contain a string 'text' field")
                texts.append(text)
            else:
                texts.append(line)
    if not texts:
        raise ValueError("Dataset contains no text records")
    return texts


def select_device(requested: str) -> torch.device:
    if requested != "auto":
        device = torch.device(requested)
        if device.type == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("CUDA was requested but is not available")
        if device.type == "mps" and not (getattr(torch.backends, "mps", None) and torch.backends.mps.is_available()):
            raise RuntimeError("MPS was requested but is not available")
        return device
    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def atomic_checkpoint(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    torch.save(payload, temporary)
    os.replace(temporary, path)


@torch.no_grad()
def evaluate(model: GPTModel, loader: DataLoader, device: torch.device, max_batches: int) -> float:
    model.eval()
    losses: list[float] = []
    for index, batch in enumerate(loader):
        if index >= max_batches:
            break
        batch = batch.to(device)
        _, loss = model(batch[:, :-1], batch[:, 1:])
        if loss is None or not torch.isfinite(loss):
            raise RuntimeError("Validation loss is non-finite")
        losses.append(float(loss.detach().cpu()))
    model.train()
    if not losses:
        raise ValueError("Validation dataset produced no batches")
    return sum(losses) / len(losses)


def train(args: argparse.Namespace) -> None:
    if min(args.steps, args.batch_size, args.checkpoint_every, args.log_every, args.eval_every, args.eval_batches) < 1:
        raise ValueError("steps, batch size and logging/evaluation/checkpoint intervals must be positive")
    if not 0.0 <= args.val_fraction < 0.5:
        raise ValueError("val-fraction must be in the range [0, 0.5)")
    if args.gradient_clip <= 0 or args.learning_rate <= 0:
        raise ValueError("gradient-clip and learning-rate must be positive")
    torch.manual_seed(args.seed)
    texts = read_corpus(Path(args.dataset))
    artifact_dir = Path(args.output_dir)
    tokenizer_path = Path(args.tokenizer) if args.tokenizer else artifact_dir / "tokenizer.json"
    if tokenizer_path.exists() and not args.retrain_tokenizer:
        tokenizer = BytePairTokenizer.load(tokenizer_path)
    else:
        tokenizer = BytePairTokenizer().train(texts, args.vocab_size, args.min_frequency)
        tokenizer.save(tokenizer_path)

    token_ids = [token for text in texts for token in tokenizer.encode(text)]
    split_index = int(len(token_ids) * (1.0 - args.val_fraction))
    training_tokens, validation_tokens = token_ids[:split_index], token_ids[split_index:]
    dataset = TokenWindowDataset(training_tokens, args.seq_len)
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True, drop_last=True)
    validation_loader = None
    if args.val_fraction > 0:
        validation_dataset = TokenWindowDataset(validation_tokens, args.seq_len)
        validation_loader = DataLoader(validation_dataset, batch_size=args.batch_size, shuffle=False)
    if not len(loader):
        raise ValueError("Training dataset is too small for batch size and sequence length")

    config = ModelConfig(tokenizer.vocab_size, args.seq_len, args.d_model, args.n_heads, args.n_layers, args.d_ff)
    device = select_device(args.device)
    model = GPTModel(config).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
    step = 0
    checkpoint = None
    if args.resume:
        checkpoint = torch.load(args.resume, map_location=device, weights_only=False)
        if checkpoint.get("tokenizer_vocab_size") != tokenizer.vocab_size or checkpoint.get("model_config") != config.to_dict():
            raise ValueError("Resume checkpoint is incompatible with tokenizer or model configuration")
        model.load_state_dict(checkpoint["model_state"])
        optimizer.load_state_dict(checkpoint["optimizer_state"])
        step = int(checkpoint["step"])

    def learning_rate_scale(current: int) -> float:
        if args.warmup_steps and current < args.warmup_steps:
            return max(1e-8, (current + 1) / args.warmup_steps)
        progress = min(1.0, max(0.0, (current - args.warmup_steps) / max(1, args.steps - args.warmup_steps)))
        return 0.5 * (1.0 + math.cos(math.pi * progress))

    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, learning_rate_scale)
    if checkpoint and "scheduler_state" in checkpoint:
        scheduler.load_state_dict(checkpoint["scheduler_state"])

    model.train()
    while step < args.steps:
        for batch in loader:
            if step >= args.steps:
                break
            batch = batch.to(device)
            optimizer.zero_grad(set_to_none=True)
            _, loss = model(batch[:, :-1], batch[:, 1:])
            if loss is None or not torch.isfinite(loss):
                raise RuntimeError("Training loss is missing or non-finite")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), args.gradient_clip)
            optimizer.step()
            scheduler.step()
            step += 1

            validation_loss = None
            if validation_loader is not None and (step % args.eval_every == 0 or step == args.steps):
                validation_loss = evaluate(model, validation_loader, device, args.eval_batches)
            if step % args.log_every == 0 or step == args.steps:
                print(json.dumps({"step": step, "loss": round(float(loss.detach().cpu()), 6), "validation_loss": validation_loss, "learning_rate": optimizer.param_groups[0]["lr"], "parameters": model.parameter_count(), "device": str(device)}), flush=True)
            if step % args.checkpoint_every == 0 or step == args.steps:
                payload = {"model_config": config.to_dict(), "model_state": model.state_dict(), "optimizer_state": optimizer.state_dict(), "scheduler_state": scheduler.state_dict(), "step": step, "training_steps": step, "validation_loss": validation_loss, "parameter_count": model.parameter_count(), "tokenizer_vocab_size": tokenizer.vocab_size, "tokenizer_format_version": tokenizer.FORMAT_VERSION, "dataset_path": Path(args.dataset).name}
                atomic_checkpoint(artifact_dir / "checkpoints" / f"step-{step:08d}.pt", payload)
                atomic_checkpoint(artifact_dir / "checkpoints" / "latest.pt", payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train the experimental Klod decoder-only model")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output-dir", default="artifacts")
    parser.add_argument("--tokenizer")
    parser.add_argument("--retrain-tokenizer", action="store_true")
    parser.add_argument("--resume")
    parser.add_argument("--steps", type=int, default=1000)
    parser.add_argument("--seq-len", type=int, default=128)
    parser.add_argument("--vocab-size", type=int, default=2048)
    parser.add_argument("--min-frequency", type=int, default=2)
    parser.add_argument("--d-model", type=int, default=256)
    parser.add_argument("--n-heads", type=int, default=4)
    parser.add_argument("--n-layers", type=int, default=4)
    parser.add_argument("--d-ff", type=int, default=1024)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--weight-decay", type=float, default=0.1)
    parser.add_argument("--gradient-clip", type=float, default=1.0)
    parser.add_argument("--warmup-steps", type=int, default=50)
    parser.add_argument("--val-fraction", type=float, default=0.05)
    parser.add_argument("--eval-every", type=int, default=100)
    parser.add_argument("--eval-batches", type=int, default=20)
    parser.add_argument("--checkpoint-every", type=int, default=100)
    parser.add_argument("--log-every", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", default="auto")
    return parser


if __name__ == "__main__":
    train(build_parser().parse_args())
