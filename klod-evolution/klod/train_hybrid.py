import argparse
import hashlib
import json
from pathlib import Path

import torch

from .hybrid_model import HybridConfig, HybridKlodModel
from .model import ByteTokenizer
from .train import read_corpus


PROFILES = {
    "micro": {
        "hidden_size": 64,
        "logical_layers": 128,
        "active_stages": 2,
        "attention_rank": 16,
        "attention_heads": 4,
        "dense_rank": 32,
        "expert_rank": 16,
        "stage_rank": 16,
        "n_experts": 4,
        "top_k_experts": 2,
        "max_seq_len": 32,
    },
    "small": {
        "hidden_size": 256,
        "logical_layers": 512,
        "active_stages": 4,
        "attention_rank": 32,
        "attention_heads": 4,
        "dense_rank": 64,
        "expert_rank": 32,
        "stage_rank": 32,
        "n_experts": 4,
        "top_k_experts": 2,
        "max_seq_len": 128,
    },
    "medium": {
        "hidden_size": 1024,
        "logical_layers": 4096,
        "active_stages": 6,
        "attention_rank": 64,
        "attention_heads": 4,
        "dense_rank": 128,
        "expert_rank": 64,
        "stage_rank": 64,
        "n_experts": 8,
        "top_k_experts": 2,
        "max_seq_len": 256,
    },
    "target": {
        "hidden_size": 40000,
        "logical_layers": 20000,
        "active_stages": 8,
        "attention_rank": 64,
        "attention_heads": 4,
        "dense_rank": 128,
        "expert_rank": 64,
        "stage_rank": 64,
        "n_experts": 8,
        "top_k_experts": 2,
        "max_seq_len": 256,
    },
}


def estimate_parameters(config: HybridConfig) -> dict:
    h = config.hidden_size
    logical = config.logical_layers
    stage_rank = config.stage_rank
    attn_rank = config.attention_rank
    dense_rank = config.dense_rank
    expert_rank = config.expert_rank
    experts = config.n_experts
    vocab = config.vocab_size
    seq_len = config.max_seq_len

    components = {
        "token_embedding": vocab * h,
        "position_embedding_and_projection": seq_len * stage_rank + stage_rank * h,
        "logical_stage_router": h * stage_rank + stage_rank + stage_rank * logical + logical,
        "logical_stage_embeddings": logical * stage_rank + stage_rank * h,
        "factorized_attention": 4 * h * attn_rank + 4 * attn_rank * attn_rank + 4 * attn_rank,
        "shared_dense_core": 2 * h * dense_rank,
        "sparse_low_rank_experts": 2 * experts * h * expert_rank,
        "expert_router": h * experts + experts,
        "sparse_gate": h + 1,
        "normalization": 8 * h,
        "language_model_head": h * attn_rank + attn_rank * vocab,
    }
    return {
        "components": components,
        "total_parameters_estimate": sum(components.values()),
        "fp16_weight_bytes_estimate": sum(components.values()) * 2,
        "fp16_weight_decimal_gb_estimate": sum(components.values()) * 2 / 1_000_000_000,
        "adamw_training_state_floor_bytes_estimate": sum(components.values()) * 16,
        "note": "Estimates exclude activations, attention workspaces, allocator fragmentation, gradient accumulation buffers and data batches.",
    }


def sample_batch(
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


def evaluate_loss(
    model: HybridKlodModel,
    data: torch.Tensor,
    seq_len: int,
    device: str,
    max_windows: int = 16,
) -> float:
    upper = data.numel() - seq_len - 1
    if upper < 1:
        raise ValueError("Validation split is too small")
    count = min(max_windows, upper)
    starts = torch.linspace(0, upper - 1, steps=count).long().unique().tolist()
    was_training = model.training
    losses = []
    model.eval()
    try:
        with torch.inference_mode():
            for start in starts:
                inputs = data[start:start + seq_len].unsqueeze(0).to(device)
                targets = data[start + 1:start + seq_len + 1].unsqueeze(0).to(device)
                _, loss = model(inputs, targets)
                if loss is None or not torch.isfinite(loss):
                    raise RuntimeError("Validation loss is not finite")
                losses.append(float(loss.detach().cpu()))
    finally:
        model.train(was_training)
    return sum(losses) / len(losses)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train the hybrid dense-sparse KLOD model"
    )
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--validation-data", type=Path)
    parser.add_argument("--profile", choices=sorted(PROFILES), default="micro")
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--seq-len", type=int)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--dtype", choices=["fp32", "bf16"], default="fp32")
    parser.add_argument("--out", type=Path, default=Path("runs/klod-hybrid.pt"))
    parser.add_argument("--eval-every", type=int, default=10)
    parser.add_argument("--patience", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--allow-cpu-target", action="store_true")
    args = parser.parse_args()

    if not 1 <= args.steps <= 1_000_000:
        raise SystemExit("--steps must be between 1 and 1000000")
    if not 1 <= args.batch_size <= 128:
        raise SystemExit("--batch-size must be between 1 and 128")
    if not 1 <= args.eval_every <= args.steps:
        raise SystemExit("--eval-every must be between 1 and steps")
    if not 1 <= args.patience <= 1000:
        raise SystemExit("--patience must be between 1 and 1000")

    settings = dict(PROFILES[args.profile])
    if args.seq_len is not None:
        settings["max_seq_len"] = args.seq_len
    config = HybridConfig(**settings)
    config.validate()

    if config.hidden_size >= 4096 and args.device.startswith("cpu") and not args.allow_cpu_target:
        raise SystemExit(
            "The wide target profile is intended for a GPU. "
            "Use --device cuda, or pass --allow-cpu-target explicitly for a slow, memory-heavy run."
        )
    if args.dtype == "bf16" and not args.device.startswith("cuda"):
        raise SystemExit("bf16 autocast is currently enabled only for CUDA in this trainer")

    tokenizer = ByteTokenizer()
    training_text = read_corpus(args.data)
    all_ids = tokenizer.encode(training_text)
    validation_source = "held-out-tail"
    if args.validation_data:
        if args.validation_data.resolve() == args.data.resolve():
            raise SystemExit("--validation-data must be different from --data")
        validation_text = read_corpus(args.validation_data)
        train_ids = all_ids
        validation_ids = tokenizer.encode(validation_text)
        validation_source = str(args.validation_data)
    else:
        split = int(len(all_ids) * 0.9)
        train_ids = all_ids[:split]
        validation_ids = all_ids[split:]
        validation_text = tokenizer.decode(validation_ids)

    seq_len = config.max_seq_len
    if len(train_ids) <= seq_len + 1 or len(validation_ids) <= seq_len + 1:
        raise SystemExit(
            f"Not enough tokens for seq_len={seq_len}: "
            f"train={len(train_ids)}, validation={len(validation_ids)}"
        )

    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    model = HybridKlodModel(config).to(args.device)
    parameter_count = model.parameter_count()
    resource_estimate = estimate_parameters(config)
    print(json.dumps({
        "profile": args.profile,
        "config": model.export_config(),
        "parameter_count": parameter_count,
        "resource_estimate": resource_estimate,
        "device": args.device,
        "dtype": args.dtype,
    }, indent=2))

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate)
    generator = torch.Generator(device="cpu").manual_seed(args.seed)
    train_data = torch.tensor(train_ids, dtype=torch.long)
    validation_data = torch.tensor(validation_ids, dtype=torch.long)
    autocast_enabled = args.dtype == "bf16"
    autocast_dtype = torch.bfloat16

    best_loss = float("inf")
    best_state = None
    best_step = 0
    stale = 0
    final_train_loss = float("inf")
    actual_steps = 0

    model.train()
    for step in range(1, args.steps + 1):
        inputs, targets = sample_batch(
            train_data,
            args.batch_size,
            seq_len,
            generator,
            args.device,
        )
        optimizer.zero_grad(set_to_none=True)
        with torch.autocast(
            device_type="cuda",
            dtype=autocast_dtype,
            enabled=autocast_enabled,
        ):
            _, loss = model(inputs, targets)
        if loss is None or not torch.isfinite(loss):
            raise RuntimeError("Training produced a non-finite loss")
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        final_train_loss = float(loss.detach().cpu())
        actual_steps = step

        if step == 1 or step % args.eval_every == 0 or step == args.steps:
            validation_loss = evaluate_loss(
                model,
                validation_data,
                seq_len,
                args.device,
            )
            print(
                f"step={step}/{args.steps} "
                f"train_loss={final_train_loss:.4f} "
                f"validation_loss={validation_loss:.4f}"
            )
            if validation_loss < best_loss:
                best_loss = validation_loss
                best_step = step
                stale = 0
                best_state = {
                    key: value.detach().cpu().clone()
                    for key, value in model.state_dict().items()
                }
            else:
                stale += 1
            if stale >= args.patience:
                print(f"early_stopping=patience_{args.patience}")
                break

    if best_state is None:
        raise RuntimeError("No valid hybrid checkpoint was produced")
    model.load_state_dict(best_state)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        "architecture_type": "hybrid_dense_sparse",
        "config": model.export_config(),
        "state_dict": model.state_dict(),
        "training": {
            "profile": args.profile,
            "requested_steps": args.steps,
            "actual_steps": actual_steps,
            "best_step": best_step,
            "final_train_loss": final_train_loss,
            "best_validation_loss": best_loss,
            "validation_source": validation_source,
            "train_tokens": len(train_ids),
            "validation_tokens": len(validation_ids),
            "corpus_sha256": hashlib.sha256(training_text.encode("utf-8")).hexdigest(),
            "validation_sha256": hashlib.sha256(validation_text.encode("utf-8")).hexdigest(),
            "parameter_count": parameter_count,
            "resource_estimate": resource_estimate,
        },
    }, args.out)
    print(
        f"checkpoint={args.out} parameters={parameter_count} "
        f"best_step={best_step} validation_loss={best_loss:.4f}"
    )


if __name__ == "__main__":
    main()
