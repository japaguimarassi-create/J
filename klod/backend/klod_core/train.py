from __future__ import annotations
import argparse
from pathlib import Path
import torch
from .model import KlodLM
from .tokenizer import ByteBPE

def make_batches(ids, block_size, batch_size, device):
    if len(ids) <= block_size + 1:
        raise ValueError("Corpus is too small for the selected block size")
    while True:
        starts = torch.randint(0, len(ids) - block_size - 1, (batch_size,))
        x = torch.stack([torch.tensor(ids[i:i + block_size], dtype=torch.long) for i in starts.tolist()]).to(device)
        y = torch.stack([torch.tensor(ids[i + 1:i + block_size + 1], dtype=torch.long) for i in starts.tolist()]).to(device)
        yield x, y

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--block-size", type=int, default=128)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--vocab-size", type=int, default=512)
    parser.add_argument("--output", default="checkpoints/klod-experimental.pt")
    args = parser.parse_args()
    if args.steps < 1:
        raise ValueError("steps must be positive")
    text = Path(args.corpus).read_text(encoding="utf-8")
    tokenizer = ByteBPE.train([text], args.vocab_size)
    ids = tokenizer.encode(text)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = KlodLM(len(tokenizer.vocab)).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4)
    stream = make_batches(ids, args.block_size, args.batch_size, device)
    model.train()
    for step in range(args.steps):
        x, y = next(stream)
        _, loss = model(x, y)
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        if (step + 1) % 10 == 0:
            print(f"step={step + 1} loss={loss.item():.4f}")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    tokenizer.save(output.with_suffix(".tokenizer.json"))
    torch.save({"model": model.state_dict(), "vocab_size": len(tokenizer.vocab), "steps": args.steps}, output)
    print(f"device={device} parameters={model.parameter_count} checkpoint={output}")

if __name__ == "__main__":
    main()
