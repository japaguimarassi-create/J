from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
from typing import Any

import torch
from torch.utils.data import DataLoader, Dataset

from klod.neural import GPTModel, ModelConfig, expand_model
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


def _load_or_train_tokenizer(
    args: argparse.Namespace,
    texts: list[str],
    tokenizer_source: Path,
    tokenizer_output: Path,
) -> BytePairTokenizer:
    retrain = bool(getattr(args, "retrain_tokenizer", False))
    expand = bool(getattr(args, "expand_tokenizer", False))
    has_source_checkpoint = bool(getattr(args, "resume", None) or getattr(args, "expand_from", None))
    if retrain and expand:
        raise ValueError("--retrain-tokenizer and --expand-tokenizer are mutually exclusive")
    if retrain and has_source_checkpoint:
        raise ValueError("A tokenizer reset cannot be combined with model resume or expansion")
    if expand:
        if not tokenizer_source.is_file():
            raise FileNotFoundError("Cannot expand a tokenizer that does not exist")
        if tokenizer_source.resolve() == tokenizer_output.resolve():
            raise ValueError("Tokenizer expansion requires a new output directory to preserve the source tokenizer")
        tokenizer = BytePairTokenizer.load(tokenizer_source)
        previous_size = tokenizer.vocab_size
        tokenizer.extend(
            texts,
            target_vocab_size=args.vocab_size,
            min_frequency=args.min_frequency,
            max_token_bytes=getattr(args, "max_token_bytes", BytePairTokenizer.DEFAULT_MAX_TOKEN_BYTES),
        )
        if tokenizer.vocab_size < previous_size:
            raise RuntimeError("Tokenizer expansion unexpectedly reduced the vocabulary")
        tokenizer.save(tokenizer_output)
        return tokenizer
    if tokenizer_source.exists() and not retrain:
        tokenizer = BytePairTokenizer.load(tokenizer_source)
        tokenizer.save(tokenizer_output)
        return tokenizer
    if has_source_checkpoint:
        raise ValueError("A source checkpoint requires its matching tokenizer; use --expand-tokenizer only to append tokens")
    tokenizer = BytePairTokenizer().train(
        texts,
        vocab_size=args.vocab_size,
        min_frequency=args.min_frequency,
        max_token_bytes=getattr(args, "max_token_bytes", BytePairTokenizer.DEFAULT_MAX_TOKEN_BYTES),
    )
    tokenizer.save(tokenizer_output)
    return tokenizer

def _model_config(args: argparse.Namespace, vocab_size: int, source: ModelConfig | None = None) -> ModelConfig:
    defaults = source
    d_model = getattr(args, "d_model", None) or (defaults.d_model if defaults else 256)
    n_heads = getattr(args, "n_heads", None) or (defaults.n_heads if defaults else 4)
    n_layers = getattr(args, "n_layers", None) or (defaults.n_layers if defaults else 4)
    d_ff = getattr(args, "d_ff", None) or (defaults.d_ff if defaults else 1024)
    max_seq_len = args.seq_len
    if defaults and args.seq_len == 128 and defaults.max_seq_len != 128:
        max_seq_len = defaults.max_seq_len
    return ModelConfig(vocab_size, max_seq_len, d_model, n_heads, n_layers, d_ff)


def train(args: argparse.Namespace) -> None:
    if getattr(args, "resume", None) and getattr(args, "expand_from", None):
        raise ValueError("--resume and --expand-from are mutually exclusive")
    if min(args.steps, args.batch_size, args.checkpoint_every, args.log_every, args.eval_every, args.eval_batches) < 1:
        raise ValueError("steps, batch size and logging/evaluation/checkpoint intervals must be positive")
    if not 0.0 <= args.val_fraction < 0.5:
        raise ValueError("val-fraction must be in the range [0, 0.5)")
    if args.gradient_clip <= 0 or args.learning_rate <= 0:
        raise ValueError("gradient-clip and learning-rate must be positive")

    torch.manual_seed(args.seed)
    texts = read_corpus(Path(args.dataset))
    artifact_dir = Path(args.output_dir).resolve()
    tokenizer_path = artifact_dir / "tokenizer.json"
    tokenizer_source = Path(args.tokenizer).resolve() if args.tokenizer else tokenizer_path
    if getattr(args, "expand_from", None):
        source_checkpoint_path = Path(args.expand_from).resolve()
        if source_checkpoint_path.is_relative_to(artifact_dir):
            raise ValueError("Model expansion requires a new output directory to preserve the parent checkpoint")
    tokenizer = _load_or_train_tokenizer(args, texts, tokenizer_source, tokenizer_path)
    token_ids = [token for text in texts for token in tokenizer.encode(text, add_bos=True, add_eos=True)]
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

    device = select_device(args.device)
    optimizer_state = None
    scheduler_state = None
    step = 0
    parent_checkpoint = None
    expansion_report = None

    if getattr(args, "resume", None):
        checkpoint = torch.load(args.resume, map_location=device, weights_only=False)
        source_config = ModelConfig(**checkpoint["model_config"])
        if checkpoint.get("tokenizer_vocab_size") != tokenizer.vocab_size:
            raise ValueError("Resume checkpoint does not match the tokenizer vocabulary")
        config = _model_config(args, tokenizer.vocab_size, source_config)
        if config.to_dict() != source_config.to_dict():
            raise ValueError("Ordinary resume requires the exact checkpoint model configuration; use --expand-from")
        model = GPTModel(source_config).to(device)
        model.load_state_dict(checkpoint["model_state"])
        optimizer_state = checkpoint["optimizer_state"]
        scheduler_state = checkpoint.get("scheduler_state")
        step = int(checkpoint.get("training_steps", checkpoint["step"]))
        parent_checkpoint = str(args.resume)
    elif getattr(args, "expand_from", None):
        checkpoint = torch.load(args.expand_from, map_location=device, weights_only=False)
        source_config = ModelConfig(**checkpoint["model_config"])
        source_vocab = int(checkpoint["tokenizer_vocab_size"])
        if tokenizer.vocab_size < source_vocab:
            raise ValueError("Expanded tokenizer is smaller than the source checkpoint vocabulary")
        source_model = GPTModel(source_config).to(device)
        source_model.load_state_dict(checkpoint["model_state"])
        config = _model_config(args, tokenizer.vocab_size, source_config)
        model, report = expand_model(source_model, config)
        model = model.to(device)
        expansion_report = {
            "previous_parameters": report.previous_parameters,
            "expanded_parameters": report.expanded_parameters,
            "copied_parameter_elements": report.copied_parameter_elements,
            "added_layers": report.added_layers,
            "added_feed_forward_width": report.added_feed_forward_width,
            "added_vocabulary_items": report.added_vocabulary_items,
        }
        step = int(checkpoint.get("training_steps", checkpoint.get("step", 0)))
        parent_checkpoint = str(args.expand_from)
    else:
        config = _model_config(args, tokenizer.vocab_size)
        model = GPTModel(config).to(device)

    if args.steps <= step:
        raise ValueError(f"--steps ({args.steps}) must exceed the source checkpoint step ({step})")

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
    if optimizer_state is not None:
        optimizer.load_state_dict(optimizer_state)

    def learning_rate_scale(current: int) -> float:
        if args.warmup_steps and current < args.warmup_steps:
            return max(1e-8, (current + 1) / args.warmup_steps)
        progress = min(1.0, max(0.0, (current - args.warmup_steps) / max(1, args.steps - args.warmup_steps)))
        return 0.5 * (1.0 + math.cos(math.pi * progress))

    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, learning_rate_scale)
    if scheduler_state is not None:
        scheduler.load_state_dict(scheduler_state)

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
                print(json.dumps({
                    "step": step,
                    "loss": round(float(loss.detach().cpu()), 6),
                    "validation_loss": validation_loss,
                    "learning_rate": optimizer.param_groups[0]["lr"],
                    "parameters": model.parameter_count(),
                    "vocab_size": tokenizer.vocab_size,
                    "tokenizer_format_version": tokenizer.FORMAT_VERSION,
                    "device": str(device),
                }), flush=True)
            if step % args.checkpoint_every == 0 or step == args.steps:
                payload = {
                    "model_config": config.to_dict(),
                    "model_state": model.state_dict(),
                    "optimizer_state": optimizer.state_dict(),
                    "scheduler_state": scheduler.state_dict(),
                    "step": step,
                    "training_steps": step,
                    "validation_loss": validation_loss,
                    "parameter_count": model.parameter_count(),
                    "tokenizer_vocab_size": tokenizer.vocab_size,
                    "tokenizer_format_version": tokenizer.FORMAT_VERSION,
                    "dataset_path": Path(args.dataset).name,
                    "parent_checkpoint": parent_checkpoint,
                    "expansion": expansion_report,
                }
                atomic_checkpoint(artifact_dir / "checkpoints" / f"step-{step:08d}.pt", payload)
                atomic_checkpoint(artifact_dir / "checkpoints" / "latest.pt", payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train the experimental Klod decoder-only model")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output-dir", default="artifacts")
    parser.add_argument("--tokenizer")
    parser.add_argument("--retrain-tokenizer", action="store_true")
    parser.add_argument("--expand-tokenizer", action="store_true")
    parser.add_argument("--resume")
    parser.add_argument("--expand-from")
    parser.add_argument("--steps", type=int, default=1000)
    parser.add_argument("--seq-len", type=int, default=128)
    parser.add_argument("--vocab-size", type=int, default=BytePairTokenizer.DEFAULT_VOCAB_SIZE)
    parser.add_argument("--min-frequency", type=int, default=2)
    parser.add_argument("--max-token-bytes", type=int, default=BytePairTokenizer.DEFAULT_MAX_TOKEN_BYTES)
    parser.add_argument("--d-model", type=int)
    parser.add_argument("--n-heads", type=int)
    parser.add_argument("--n-layers", type=int)
    parser.add_argument("--d-ff", type=int)
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
