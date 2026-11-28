import argparse
import hashlib
import json
from pathlib import Path

import torch

from .model import ByteTokenizer, KlodModel, ModelConfig


def _format_messages(messages: list) -> str:
    lines = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        role = str(message.get("role", "user")).lower()
        content = message.get("content") or message.get("text")
        if not isinstance(content, str) or not content.strip():
            continue
        speaker = "KLOD" if role in {"assistant", "system"} else "Usuário"
        lines.append(f"{speaker}: {content.strip()}")
    return "\n".join(lines)


def read_corpus(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(path)
    if path.suffix.lower() == ".jsonl":
        entries = []
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            item = json.loads(line)
            if not isinstance(item, dict):
                raise ValueError(f"JSONL line {line_number} must contain an object")
            text = item.get("text") or item.get("content")
            if isinstance(text, str) and text.strip():
                entries.append(text.strip())
                continue
            messages = item.get("messages")
            if isinstance(messages, list):
                formatted = _format_messages(messages)
                if formatted:
                    entries.append(formatted)
                    continue
            prompt = item.get("prompt") or item.get("instruction")
            completion = item.get("completion") or item.get("response") or item.get("output")
            if isinstance(prompt, str) and isinstance(completion, str):
                entries.append(f"Usuário: {prompt.strip()}\nKLOD: {completion.strip()}")
            elif isinstance(completion, str) and completion.strip():
                entries.append(completion.strip())
        return "\n\n".join(entries)
    return path.read_text(encoding="utf-8")


def _sample_batch(
    data: torch.Tensor,
    batch_size: int,
    seq_len: int,
    generator: torch.Generator,
    device: str,
) -> tuple[torch.Tensor, torch.Tensor]:
    upper = data.numel() - seq_len - 1
    if upper < 1:
        raise ValueError("Dataset split is too small for the selected sequence length")
    starts = torch.randint(0, upper, (batch_size,), generator=generator)
    inputs = torch.stack([data[start:start + seq_len] for start in starts]).to(device)
    targets = torch.stack([data[start + 1:start + seq_len + 1] for start in starts]).to(device)
    return inputs, targets


def mean_loss(model: KlodModel, data: torch.Tensor, seq_len: int, max_windows: int = 64) -> float:
    upper = data.numel() - seq_len - 1
    if upper < 1:
        raise ValueError("Evaluation split is too small for the selected sequence length")
    count = min(max_windows, upper)
    starts = torch.linspace(0, upper - 1, steps=count).long().unique().tolist()
    losses = []
    model.eval()
    with torch.inference_mode():
        for start in starts:
            inputs = data[start:start + seq_len].unsqueeze(0)
            targets = data[start + 1:start + seq_len + 1].unsqueeze(0)
            _, loss = model(inputs, targets)
            if loss is None or not torch.isfinite(loss):
                raise RuntimeError("Evaluation produced a non-finite loss")
            losses.append(float(loss.detach().cpu()))
    model.train()
    return sum(losses) / len(losses)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a KLOD model with validation and early stopping")
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--validation-data", type=Path)
    parser.add_argument("--steps", type=int, default=1000)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--seq-len", type=int, default=128)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--out", type=Path, default=Path("runs/klod.pt"))
    parser.add_argument("--layers", type=int, default=6)
    parser.add_argument("--width", type=int, default=128)
    parser.add_argument("--heads", type=int, default=4)
    parser.add_argument("--experts", type=int, default=4)
    parser.add_argument("--eval-every", type=int, default=100)
    parser.add_argument("--patience", type=int, default=8)
    parser.add_argument("--min-delta", type=float, default=0.001)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if not 1 <= args.steps <= 1_000_000:
        raise SystemExit("--steps must be between 1 and 1000000")
    if not 1 <= args.batch_size <= 256:
        raise SystemExit("--batch-size must be between 1 and 256")
    if not 8 <= args.seq_len <= 8192:
        raise SystemExit("--seq-len must be between 8 and 8192")
    if not 1 <= args.eval_every <= args.steps:
        raise SystemExit("--eval-every must be between 1 and steps")
    if not 1 <= args.patience <= 1000:
        raise SystemExit("--patience must be between 1 and 1000")
    if args.min_delta < 0:
        raise SystemExit("--min-delta must be non-negative")

    tokenizer = ByteTokenizer()
    training_text = read_corpus(args.data)
    all_train_ids = tokenizer.encode(training_text)
    validation_source = "held-out-tail"
    if args.validation_data:
        validation_text = read_corpus(args.validation_data)
        train_ids = all_train_ids
        validation_ids = tokenizer.encode(validation_text)
        validation_source = str(args.validation_data)
    else:
        split = int(len(all_train_ids) * 0.9)
        train_ids = all_train_ids[:split]
        validation_ids = all_train_ids[split:]
        validation_text = tokenizer.decode(validation_ids)

    if len(train_ids) <= args.seq_len + 1 or len(validation_ids) <= args.seq_len + 1:
        raise SystemExit(
            f"Not enough tokens for train/validation with seq_len={args.seq_len}: "
            f"train={len(train_ids)}, validation={len(validation_ids)}. "
            "Provide more data or reduce --seq-len."
        )

    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    train_data = torch.tensor(train_ids, dtype=torch.long)
    validation_data = torch.tensor(validation_ids, dtype=torch.long)
    config = ModelConfig(
        vocab_size=tokenizer.vocab_size,
        d_model=args.width,
        n_heads=args.heads,
        n_layers=args.layers,
        n_experts=args.experts,
        max_seq_len=args.seq_len,
    )
    model = KlodModel(config).to(args.device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr)
    generator = torch.Generator(device="cpu").manual_seed(args.seed)

    best_validation_loss = float("inf")
    best_state = None
    best_step = 0
    stale_evaluations = 0
    final_train_loss = float("inf")
    actual_steps = 0

    model.train()
    for step in range(1, args.steps + 1):
        batch_x, batch_y = _sample_batch(
            train_data,
            args.batch_size,
            args.seq_len,
            generator,
            args.device,
        )
        optimizer.zero_grad(set_to_none=True)
        _, loss = model(batch_x, batch_y)
        if loss is None or not torch.isfinite(loss):
            raise RuntimeError("Training produced a non-finite loss")
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        final_train_loss = float(loss.detach().cpu())
        actual_steps = step

        should_evaluate = step == 1 or step % args.eval_every == 0 or step == args.steps
        if not should_evaluate:
            continue

        validation_loss = mean_loss(model, validation_data, args.seq_len)
        improved = validation_loss < best_validation_loss - args.min_delta
        if improved:
            best_validation_loss = validation_loss
            best_step = step
            stale_evaluations = 0
            best_state = {
                key: value.detach().cpu().clone()
                for key, value in model.state_dict().items()
            }
        else:
            stale_evaluations += 1

        print(
            f"step={step}/{args.steps} train_loss={final_train_loss:.4f} "
            f"validation_loss={validation_loss:.4f} best={best_validation_loss:.4f}"
        )
        if stale_evaluations >= args.patience:
            print(f"early_stopping=patience_{args.patience}")
            break

    if best_state is None:
        raise RuntimeError("Training ended without a valid checkpoint state")
    model.load_state_dict(best_state)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        "config": model.export_config(),
        "state_dict": model.state_dict(),
        "training": {
            "requested_steps": args.steps,
            "actual_steps": actual_steps,
            "best_step": best_step,
            "final_batch_loss": final_train_loss,
            "best_validation_loss": best_validation_loss,
            "validation_source": validation_source,
            "train_tokens": len(train_ids),
            "validation_tokens": len(validation_ids),
            "corpus_sha256": hashlib.sha256(training_text.encode("utf-8")).hexdigest(),
            "validation_sha256": hashlib.sha256(validation_text.encode("utf-8")).hexdigest(),
        },
    }, args.out)
    print(
        f"checkpoint={args.out} best_step={best_step} "
        f"best_validation_loss={best_validation_loss:.4f}"
    )


if __name__ == "__main__":
    main()
