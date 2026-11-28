import argparse
import hashlib
import json
import random
from pathlib import Path

import torch

from .model import ByteTokenizer, KlodModel, ModelConfig
from .shard_plan import PROFILES
from .train import mean_loss, read_corpus


def train_one_shard(
    shard: dict,
    base_dir: Path,
    output_dir: Path,
    profile: str,
    steps: int,
    batch_size: int,
    seq_len: int,
    device: str,
    seed: int,
    overrides: dict,
) -> dict:
    shard_id = shard["id"]
    corpus_path = (base_dir / shard["corpus"]).resolve()
    corpus = read_corpus(corpus_path)
    tokenizer = ByteTokenizer()
    tokens = tokenizer.encode(corpus)

    split = int(len(tokens) * 0.9)
    train_ids = tokens[:split]
    validation_ids = tokens[split:]
    if len(train_ids) <= seq_len + 1 or len(validation_ids) <= seq_len + 1:
        raise ValueError(
            f"{shard_id}: insufficient tokens for seq_len={seq_len}; "
            f"train={len(train_ids)}, validation={len(validation_ids)}"
        )

    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    selected_profile = dict(PROFILES[profile])
    selected_profile.update({key: value for key, value in overrides.items() if value is not None})
    width = selected_profile["width"]
    heads = selected_profile["heads"]
    layers = selected_profile["layers"]
    experts = selected_profile["experts"]
    if width % heads:
        raise ValueError(f"{shard_id}: width {width} must be divisible by heads {heads}")

    config = ModelConfig(
        vocab_size=tokenizer.vocab_size,
        d_model=width,
        n_heads=heads,
        n_layers=layers,
        n_experts=experts,
        max_seq_len=seq_len,
        dropout=0.05,
    )
    model = KlodModel(config).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=selected_profile.get("lr", 3e-4))
    generator = torch.Generator(device="cpu").manual_seed(seed)
    train_data = torch.tensor(train_ids, dtype=torch.long)
    validation_data = torch.tensor(validation_ids, dtype=torch.long)
    best_loss = float("inf")
    best_state = None
    best_step = 0
    started_loss = mean_loss(model, train_data, seq_len)

    for step in range(1, steps + 1):
        upper = train_data.numel() - seq_len - 1
        starts = torch.randint(0, upper, (batch_size,), generator=generator)
        inputs = torch.stack([train_data[start:start + seq_len] for start in starts]).to(device)
        targets = torch.stack([train_data[start + 1:start + seq_len + 1] for start in starts]).to(device)
        model.train()
        optimizer.zero_grad(set_to_none=True)
        _, loss = model(inputs, targets)
        if loss is None or not torch.isfinite(loss):
            raise RuntimeError(f"{shard_id}: non-finite training loss")
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()

        current_validation = mean_loss(model, validation_data, seq_len)
        if current_validation < best_loss:
            best_loss = current_validation
            best_step = step
            best_state = {
                key: value.detach().cpu().clone()
                for key, value in model.state_dict().items()
            }

    if best_state is None:
        raise RuntimeError(f"{shard_id}: no valid checkpoint state was produced")

    model.load_state_dict(best_state)
    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint = output_dir / f"{shard_id}.pt"
    training_info = {
        "shard_id": shard_id,
        "domain": shard.get("domain", shard_id),
        "profile": profile,
        "steps": steps,
        "best_step": best_step,
        "initial_train_loss": started_loss,
        "best_validation_loss": best_loss,
        "train_tokens": len(train_ids),
        "validation_tokens": len(validation_ids),
        "corpus_sha256": hashlib.sha256(corpus.encode("utf-8")).hexdigest(),
        "seed": seed,
    }
    torch.save({
        "config": model.export_config(),
        "state_dict": model.state_dict(),
        "training": training_info,
    }, checkpoint)
    return {
        **training_info,
        "checkpoint": str(checkpoint),
        "parameter_count": sum(parameter.numel() for parameter in model.parameters()),
        "checkpoint_bytes": checkpoint.stat().st_size,
        "passed": checkpoint.is_file() and checkpoint.stat().st_size > 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train capability shards independently and save one checkpoint per shard"
    )
    parser.add_argument("--manifest", type=Path, default=Path("config/shards.json"))
    parser.add_argument("--profile", choices=sorted(PROFILES), default="small")
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--seq-len", type=int, default=64)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--checkpoint-dir", type=Path, default=Path("runs/shards"))
    parser.add_argument("--report", type=Path, default=Path("runs/shards/training-report.json"))
    parser.add_argument("--only", default="")
    parser.add_argument("--width", type=int)
    parser.add_argument("--layers", type=int)
    parser.add_argument("--heads", type=int)
    parser.add_argument("--experts", type=int)
    parser.add_argument("--seed", type=int, default=1402)
    parser.add_argument("--continue-on-error", action="store_true")
    args = parser.parse_args()

    if not 1 <= args.steps <= 1_000_000:
        raise SystemExit("--steps must be between 1 and 1000000")
    if not 1 <= args.batch_size <= 256:
        raise SystemExit("--batch-size must be between 1 and 256")
    if not 8 <= args.seq_len <= 8192:
        raise SystemExit("--seq-len must be between 8 and 8192")

    manifest_path = args.manifest.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    base_dir = manifest_path.parent.parent
    shards = manifest.get("shards", [])
    if args.only.strip():
        selected = {item.strip() for item in args.only.split(",") if item.strip()}
        shards = [shard for shard in shards if shard["id"] in selected]
        missing = selected - {shard["id"] for shard in shards}
        if missing:
            raise SystemExit(f"Unknown shard IDs: {', '.join(sorted(missing))}")
    if not shards:
        raise SystemExit("No shards selected")

    overrides = {
        "width": args.width,
        "layers": args.layers,
        "heads": args.heads,
        "experts": args.experts,
    }
    results = []
    failures = []

    for index, shard in enumerate(shards):
        try:
            result = train_one_shard(
                shard=shard,
                base_dir=base_dir,
                output_dir=args.checkpoint_dir.resolve(),
                profile=args.profile,
                steps=args.steps,
                batch_size=args.batch_size,
                seq_len=args.seq_len,
                device=args.device,
                seed=args.seed + index,
                overrides=overrides,
            )
            results.append(result)
            print(
                f"trained={result['shard_id']} parameters={result['parameter_count']} "
                f"validation_loss={result['best_validation_loss']:.4f}"
            )
        except Exception as exc:
            failure = {
                "shard_id": shard.get("id", "unknown"),
                "passed": False,
                "error": f"{type(exc).__name__}: {exc}",
            }
            failures.append(failure)
            results.append(failure)
            print(json.dumps(failure, ensure_ascii=False))
            if not args.continue_on_error:
                break

    report = {
        "manifest": str(manifest_path),
        "profile": args.profile,
        "device": args.device,
        "steps_per_shard": args.steps,
        "trained": sum(item.get("passed", False) for item in results),
        "failed": len(failures),
        "results": results,
        "note": "Each checkpoint is trained independently. Separate capability models are not equivalent to training the full dense 40k x 60k tensor.",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
