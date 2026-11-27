import argparse
import hashlib
import json
from pathlib import Path

import torch

from .model import ByteTokenizer, KlodModel, ModelConfig


def read_corpus(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(path)
    if path.suffix.lower() == ".jsonl":
        entries = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            text = item.get("text") or item.get("completion") or item.get("content")
            if isinstance(text, str):
                entries.append(text)
        return "\n".join(entries)
    return path.read_text(encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a small KLOD model from a local text corpus")
    parser.add_argument("--data", type=Path, required=True)
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
    args = parser.parse_args()

    if not 1 <= args.steps <= 1_000_000:
        raise SystemExit("--steps must be between 1 and 1000000")
    if not 1 <= args.batch_size <= 256:
        raise SystemExit("--batch-size must be between 1 and 256")
    if not 8 <= args.seq_len <= 8192:
        raise SystemExit("--seq-len must be between 8 and 8192")

    corpus = read_corpus(args.data)
    tokenizer = ByteTokenizer()
    token_ids = tokenizer.encode(corpus)
    if len(token_ids) < args.seq_len + 1:
        raise SystemExit(f"Corpus too small: need at least {args.seq_len + 1} tokens")
    data = torch.tensor(token_ids, dtype=torch.long)
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
    generator = torch.Generator(device="cpu").manual_seed(42)

    model.train()
    last_loss = None
    for step in range(1, args.steps + 1):
        starts = torch.randint(0, len(data) - args.seq_len - 1, (args.batch_size,), generator=generator)
        batch_x = torch.stack([data[start:start + args.seq_len] for start in starts]).to(args.device)
        batch_y = torch.stack([data[start + 1:start + args.seq_len + 1] for start in starts]).to(args.device)
        optimizer.zero_grad(set_to_none=True)
        _, loss = model(batch_x, batch_y)
        if loss is None or not torch.isfinite(loss):
            raise RuntimeError("Training produced a non-finite loss")
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        last_loss = float(loss.detach().cpu())
        if step == 1 or step % max(1, args.steps // 10) == 0:
            print(f"step={step}/{args.steps} loss={last_loss:.4f}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        "config": model.export_config(),
        "state_dict": model.state_dict(),
        "training": {
            "steps": args.steps,
            "final_loss": last_loss,
            "corpus_sha256": hashlib.sha256(corpus.encode("utf-8")).hexdigest(),
            "corpus_tokens": len(token_ids),
        },
    }, args.out)
    print(f"checkpoint={args.out} final_loss={last_loss:.4f}")


if __name__ == "__main__":
    main()
