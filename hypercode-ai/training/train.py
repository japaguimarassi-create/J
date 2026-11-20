import argparse
import json
import math
import random
from pathlib import Path

import torch
from torch.nn import functional as F

from model import HyperInterNetwork, smoke_config, target_config
from tokenizer import ProceduralTokenizer, VOCAB_SIZE


DOMAIN_IDS = {
    "lua_python": 0,
    "web": 1,
    "java": 2,
    "systems": 3,
    "csharp": 4,
    "algorithms": 5,
    "debugging": 6,
}
DOMAIN_ALIASES = {
    "lua": 0, "luau": 0, "python": 0,
    "javascript": 1, "typescript": 1, "html": 1, "css": 1, "web": 1,
    "java": 2, "c": 3, "cpp": 3, "c++": 3,
    "csharp": 4, "c#": 4,
    "algorithm": 5, "algorithms": 5, "data": 5,
    "debug": 6, "debugging": 6, "review": 6,
}


def infer_domain(sample):
    value = str(sample.get("domain", sample.get("language", "algorithms"))).lower()
    return DOMAIN_ALIASES.get(value, DOMAIN_IDS.get(value, 5))


def read_corpus(path, tokenizer, context_length):
    samples = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            text = row.get("text")
            if not isinstance(text, str) or not text.strip():
                continue
            ids = tokenizer.encode(text, language=row.get("language"), code=row.get("kind") == "code")
            if len(ids) >= 3:
                samples.append((infer_domain(row), ids[:context_length + 1]))
    if not samples:
        raise ValueError("The JSONL corpus contains no usable text records.")
    return samples


def make_batch(samples, domain_id, batch_size, context_length, device):
    candidates = [tokens for domain, tokens in samples if domain == domain_id and len(tokens) >= 3]
    if not candidates:
        candidates = [tokens for _, tokens in samples if len(tokens) >= 3]
    rows = []
    for _ in range(batch_size):
        tokens = random.choice(candidates)
        if len(tokens) > context_length + 1:
            start = random.randrange(0, len(tokens) - context_length)
            tokens = tokens[start:start + context_length + 1]
        else:
            tokens = list(tokens)
        rows.append(tokens + [0] * (context_length + 1 - len(tokens)))
    tensor = torch.tensor(rows, dtype=torch.long, device=device)
    return tensor[:, :-1], tensor[:, 1:]


def train(args):
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    config = target_config() if args.profile == "target" else smoke_config()
    config["vocab_size"] = VOCAB_SIZE
    tokenizer = ProceduralTokenizer()
    samples = read_corpus(args.data, tokenizer, config["context_length"])
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if args.profile == "target" and device.type != "cuda":
        raise RuntimeError("The target architecture requires a CUDA GPU with substantial memory.")
    model = HyperInterNetwork(**config).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, betas=(0.9, 0.95), weight_decay=0.1)
    scaler = torch.amp.GradScaler("cuda", enabled=device.type == "cuda")
    model.train()
    domain_ids = sorted({domain for domain, _ in samples})
    args.output.mkdir(parents=True, exist_ok=True)
    print(json.dumps({
        "profile": args.profile,
        "device": str(device),
        "samples": len(samples),
        "domains": domain_ids,
        "parameters": sum(parameter.numel() for parameter in model.parameters()),
        "architecture": config,
    }, ensure_ascii=False))

    for step in range(1, args.steps + 1):
        domain_id = random.choice(domain_ids)
        input_ids, targets = make_batch(samples, domain_id, args.batch_size, config["context_length"], device)
        warmup = min(1.0, step / max(1, args.warmup_steps))
        decay = max(0.05, 0.5 * (1.0 + math.cos(math.pi * step / max(1, args.steps))))
        for group in optimizer.param_groups:
            group["lr"] = args.learning_rate * warmup * decay
        optimizer.zero_grad(set_to_none=True)
        with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=device.type == "cuda"):
            logits = model(input_ids, domain_id)
            loss = F.cross_entropy(logits.reshape(-1, VOCAB_SIZE), targets.reshape(-1), ignore_index=0)
        scaler.scale(loss).backward()
        scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        scaler.step(optimizer)
        scaler.update()
        if step == 1 or step % args.log_every == 0 or step == args.steps:
            print(f"step={step}/{args.steps} domain={domain_id} loss={loss.item():.5f}")

    payload = {
        "state_dict": model.state_dict(),
        "config": config,
        "optimizer": optimizer.state_dict(),
        "training_steps": args.steps,
        "objective": "causal_next_byte_prediction",
        "domain_ids": DOMAIN_IDS,
    }
    torch.save(payload, args.output / "hyperinter_checkpoint.pt")
    (args.output / "model_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    (args.output / "training_metadata.json").write_text(json.dumps({
        "profile": args.profile,
        "steps": args.steps,
        "samples": len(samples),
        "objective": "causal_next_byte_prediction",
        "parameters": sum(parameter.numel() for parameter in model.parameters()),
    }, indent=2), encoding="utf-8")
    print(f"checkpoint={args.output / 'hyperinter_checkpoint.pt'}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=("smoke", "target"), default="smoke")
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("artifacts"))
    parser.add_argument("--steps", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--warmup-steps", type=int, default=10)
    parser.add_argument("--log-every", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if args.steps < 1 or args.batch_size < 1:
        parser.error("steps and batch-size must be positive.")
    train(args)


if __name__ == "__main__":
    main()
