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


class TokenWindowDataset(Dataset):
    def __init__(self, tokens: list[int], sequence_length: int) -> None:
        if len(tokens) <= sequence_length:
            raise ValueError("Corpus must contain more tokens than --seq-len")
        self.tokens = torch.tensor(tokens, dtype=torch.long)
        self.sequence_length = sequence_length

    def __len__(self) -> int:
        return self.tokens.numel() - self.sequence_length

    def __getitem__(self, index: int) -> torch.Tensor:
        return self.tokens[index:index + self.sequence_length + 1]


def read_corpus(path: Path) -> list[str]:
    texts = []
    for number, raw in enumerate(path.open("r", encoding="utf-8"), start=1):
        line = raw.rstrip("\n")
        if not line:
            continue
        if path.suffix.lower() == ".jsonl":
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSONL at line {number}: {error}") from error
            text = record.get("text") if isinstance(record, dict) else None
            if not isinstance(text, str):
                raise ValueError(f"Line {number} must contain a string text field")
            texts.append(text)
        else:
            texts.append(line)
    if not texts:
        raise ValueError("Dataset contains no text records")
    return texts


def atomic_checkpoint(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    torch.save(payload, temporary)
    os.replace(temporary, path)


def train(args: argparse.Namespace) -> None:
    if min(args.steps, args.batch_size, args.checkpoint_every, args.log_every) < 1:
        raise ValueError("steps, batch size and logging/checkpoint intervals must be positive")
    if args.gradient_clip <= 0 or args.learning_rate <= 0:
        raise ValueError("gradient clip and learning rate must be positive")
    torch.manual_seed(args.seed)
    texts = read_corpus(Path(args.dataset))
    output_dir = Path(args.output_dir)
    tokenizer_path = Path(args.tokenizer) if args.tokenizer else output_dir / "tokenizer.json"
    if tokenizer_path.exists() and not args.retrain_tokenizer:
        tokenizer = BytePairTokenizer.load(tokenizer_path)
    else:
        tokenizer = BytePairTokenizer().train(texts, args.vocab_size, args.min_frequency)
        tokenizer.save(tokenizer_path)
    tokens = [token for text in texts for token in tokenizer.encode(text)]
    dataset = TokenWindowDataset(tokens, args.seq_len)
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True, drop_last=True)
    if not len(loader):
        raise ValueError("Dataset is too small for batch size and sequence length")

    config = ModelConfig(tokenizer.vocab_size, args.seq_len, args.d_model, args.n_heads, args.n_layers, args.d_ff)
    if args.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable")
    if device.type == "mps" and not (getattr(torch.backends, "mps", None) and torch.backends.mps.is_available()):
        raise RuntimeError("MPS requested but unavailable")

    model = GPTModel(config).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
    step = 0
    checkpoint = None
    if args.resume:
        checkpoint = torch.load(args.resume, map_location=device, weights_only=False)
        if checkpoint.get("tokenizer_vocab_size") != tokenizer.vocab_size or checkpoint.get("model_config") != config.to_dict():
            raise ValueError("Resume checkpoint is incompatible with tokenizer or model config")
        model.load_state_dict(checkpoint["model_state"])
        optimizer.load_state_dict(checkpoint["optimizer_state"])
        step = int(checkpoint["step"])

    def scale(current: int) -> float:
        if args.warmup_steps and current < args.warmup_steps:
            return max(1e-8, (current + 1) / args.warmup_steps)
        progress = min(1.0, max(0.0, (current - args.warmup_steps) / max(1, args.steps - args.warmup_steps)))
        return 0.5 * (1.0 + math.cos(math.pi * progress))

    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, scale)
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
                raise RuntimeError("Training loss is non-finite")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), args.gradient_clip)
            optimizer.step()
            scheduler.step()
            step += 1
            if step % args.log_every == 0 or step == args.steps:
                print(json.dumps({"step": step, "loss": round(float(loss.detach().cpu()), 6), "parameters": model.parameter_count(), "device": str(device)}), flush=True)
            if step % args.checkpoint_every == 0 or step == args.steps:
                payload = {"model_config": config.to_dict(), "model_state": model.state_dict(), "optimizer_state": optimizer.state_dict(), "scheduler_state": scheduler.state_dict(), "step": step, "training_steps": step, "parameter_count": model.parameter_count(), "tokenizer_vocab_size": tokenizer.vocab_size, "dataset_path": Path(args.dataset).name}
                atomic_checkpoint(output_dir / "checkpoints" / f"step-{step:08d}.pt", payload)
                atomic_checkpoint(output_dir / "checkpoints" / "latest.pt", payload)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Train Klod's experimental decoder-only model")
    result.add_argument("--dataset", required=True)
    result.add_argument("--output-dir", default="artifacts")
    result.add_argument("--tokenizer")
    result.add_argument("--retrain-tokenizer", action="store_true")
    result.add_argument("--resume")
    result.add_argument("--steps", type=int, default=1000)
    result.add_argument("--seq-len", type=int, default=128)
    result.add_argument("--vocab-size", type=int, default=2048)
    result.add_argument("--min-frequency", type=int, default=2)
    result.add_argument("--d-model", type=int, default=256)
    result.add_argument("--n-heads", type=int, default=4)
    result.add_argument("--n-layers", type=int, default=4)
    result.add_argument("--d-ff", type=int, default=1024)
    result.add_argument("--batch-size", type=int, default=8)
    result.add_argument("--learning-rate", type=float, default=3e-4)
    result.add_argument("--weight-decay", type=float, default=0.1)
    result.add_argument("--gradient-clip", type=float, default=1.0)
    result.add_argument("--warmup-steps", type=int, default=50)
    result.add_argument("--checkpoint-every", type=int, default=100)
    result.add_argument("--log-every", type=int, default=10)
    result.add_argument("--seed", type=int, default=42)
    result.add_argument("--device", default="auto")
    return result


if __name__ == "__main__":
    train(parser().parse_args())
