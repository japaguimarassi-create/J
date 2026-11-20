import argparse
import gzip
import json
import random
from pathlib import Path

import torch
from torch.nn import functional as F

from model import HyperInterNetwork, smoke_config, target_config
from optimization import build_adamw, wsd_multiplier
from tokenizer import load_tokenizer


def split_by_repository(records, seed=2026):
    groups = {}
    for index, (repository, document) in enumerate(records):
        key = str(repository).strip() if repository else f"__document_{index}"
        groups.setdefault(key, []).append(document)
    if len(groups) < 2:
        raise ValueError("At least two repository groups are required for train/validation split.")
    keys = list(groups)
    random.Random(seed).shuffle(keys)
    split = max(1, int(len(keys) * 0.9))
    train_documents = [document for key in keys[:split] for document in groups[key]]
    validation_documents = [document for key in keys[split:] for document in groups[key]]
    return train_documents, validation_documents


def read_corpus(path, tokenizer, context_length):
    records = []
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSONL at line {line_number}: {error}") from error
            text = row.get("text")
            if not isinstance(text, str) or not text.strip():
                continue
            ids = tokenizer.encode(text, language=row.get("language"), code=row.get("kind") == "code")
            if len(ids) >= 3:
                records.append((row.get("repository"), ids))
    if len(records) < 2:
        raise ValueError("At least two usable documents are required for train/validation split.")
    train_documents, validation_documents = split_by_repository(records)

    def chunk_documents(items):
        chunks = []
        for document in items:
            for start in range(0, len(document) - 1, context_length):
                chunk = document[start:start + context_length + 1]
                if len(chunk) >= 3:
                    chunks.append(chunk)
        return chunks

    train_chunks = chunk_documents(train_documents)
    validation_chunks = chunk_documents(validation_documents)
    if not train_chunks or not validation_chunks:
        raise ValueError("The corpus is too small to create train/validation token chunks.")
    return train_chunks, validation_chunks


def make_batch(samples, batch_size, context_length, device):
    rows = []
    for _ in range(batch_size):
        tokens = random.choice(samples)
        if len(tokens) > context_length + 1:
            start = random.randrange(0, len(tokens) - context_length)
            tokens = tokens[start:start + context_length + 1]
        else:
            tokens = list(tokens)
        rows.append(tokens + [0] * (context_length + 1 - len(tokens)))
    tensor = torch.tensor(rows, dtype=torch.long, device=device)
    return tensor[:, :-1], tensor[:, 1:]


def language_model_loss(logits, targets):
    return F.cross_entropy(
        logits.reshape(-1, logits.size(-1)),
        targets.reshape(-1),
        ignore_index=0,
    )


def evaluate_loss(model, samples, batch_size, context_length, device, batches=4):
    model.eval()
    totals = {"collective": 0.0, "experts": [0.0] * 7}
    count = 0
    with torch.no_grad():
        for _ in range(batches):
            inputs, targets = make_batch(samples, batch_size, context_length, device)
            final_logits, auxiliary = model(inputs, return_aux=True)
            totals["collective"] += language_model_loss(final_logits, targets).item()
            for index in range(7):
                totals["experts"][index] += language_model_loss(auxiliary[:, index], targets).item()
            count += 1
    model.train()
    return {
        "collective_loss": totals["collective"] / count,
        "expert_losses": [value / count for value in totals["experts"]],
    }


def train(args):
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    config = target_config() if args.profile == "target" else smoke_config()
    if args.profile == "target" and args.tokenizer_json is None:
        raise RuntimeError("Target training requires a trained BPE tokenizer. Run train_bpe_tokenizer.py first.")
    tokenizer = load_tokenizer(args.tokenizer_json)
    config["vocab_size"] = tokenizer.vocab_size
    train_samples, validation_samples = read_corpus(args.data, tokenizer, config["context_length"])
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if args.profile == "target" and device.type != "cuda":
        raise RuntimeError("The exact target network requires a CUDA GPU. No fallback model will be passed off as the target.")
    if args.profile == "target" and not torch.cuda.is_bf16_supported():
        raise RuntimeError("Target training requires a CUDA GPU with BF16 support for this training profile.")

    model = HyperInterNetwork(**config).to(device)
    model.set_gradient_checkpointing(args.gradient_checkpointing or args.profile == "target")
    optimizer = build_adamw(
        model,
        learning_rate=args.learning_rate,
        weight_decay=args.weight_decay,
        fused=device.type == "cuda",
    )
    use_bf16 = device.type == "cuda" and torch.cuda.is_bf16_supported()
    scaler = torch.amp.GradScaler("cuda", enabled=device.type == "cuda" and not use_bf16)
    args.output.mkdir(parents=True, exist_ok=True)
    parameter_count = sum(parameter.numel() for parameter in model.parameters())
    before = evaluate_loss(model, validation_samples, args.batch_size, config["context_length"], device)
    metadata = {
        "profile": args.profile,
        "device": str(device),
        "train_records": len(train_samples),
        "validation_records": len(validation_samples),
        "parameters": parameter_count,
        "architecture": config,
        "validation_before": before,
    }
    effective_warmup_steps = min(args.warmup_steps, max(1, args.steps // 10))
    metadata["effective_warmup_steps"] = effective_warmup_steps
    metadata["scheduler"] = "warmup_stable_decay"

    print(json.dumps(metadata, ensure_ascii=False))

    model.train()
    for step in range(1, args.steps + 1):
        for group in optimizer.param_groups:
            group["lr"] = args.learning_rate * wsd_multiplier(
                step, args.steps, effective_warmup_steps, args.decay_ratio
            )
        optimizer.zero_grad(set_to_none=True)
        accumulated_loss = 0.0
        collective_loss_value = 0.0
        auxiliary_loss_value = 0.0
        for _ in range(args.gradient_accumulation_steps):
            inputs, targets = make_batch(
                train_samples,
                args.batch_size,
                config["context_length"],
                device,
            )
            with torch.autocast(
                device_type=device.type,
                dtype=torch.bfloat16 if use_bf16 else torch.float16,
                enabled=device.type == "cuda",
            ):
                final_logits, auxiliary_logits = model(inputs, return_aux=True)
                final_loss = language_model_loss(final_logits, targets)
                auxiliary_losses = [
                    language_model_loss(auxiliary_logits[:, index], targets)
                    for index in range(7)
                ]
                auxiliary_loss = torch.stack(auxiliary_losses).mean()
                loss = (final_loss + args.auxiliary_loss_weight * auxiliary_loss) / args.gradient_accumulation_steps
            if not torch.isfinite(loss):
                raise FloatingPointError(f"Non-finite loss at step {step}.")
            accumulated_loss += loss.detach().item()
            collective_loss_value += final_loss.detach().item() / args.gradient_accumulation_steps
            auxiliary_loss_value += auxiliary_loss.detach().item() / args.gradient_accumulation_steps
            scaler.scale(loss).backward()
        scaler.unscale_(optimizer)
        gradient_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), args.max_grad_norm)
        if not torch.isfinite(gradient_norm):
            raise FloatingPointError(f"Non-finite gradient norm at step {step}.")
        scaler.step(optimizer)
        scaler.update()
        if step == 1 or step % args.log_every == 0 or step == args.steps:
            print(
                f"step={step}/{args.steps} total={accumulated_loss:.5f} "
                f"collective={collective_loss_value:.5f} experts={auxiliary_loss_value:.5f} "
                f"grad_norm={float(gradient_norm):.5f}"
            )

    after = evaluate_loss(model, validation_samples, args.batch_size, config["context_length"], device)
    checkpoint_path = args.output / "hyperinter_checkpoint.pt"
    torch.save({
        "state_dict": model.state_dict(),
        "config": config,
        "training_steps": args.steps,
        "objective": "shared_causal_next_token_prediction",
        "expert_count": 7,
        "all_experts_receive_every_sample": True,
        "mutual_message_passing_layers": config["expert_layers"],
        "auxiliary_loss_weight": args.auxiliary_loss_weight,
        "tokenizer_vocab_size": tokenizer.vocab_size,
        "tokenizer_json": str(args.tokenizer_json) if args.tokenizer_json else None,
        "training_recipe": "AdamW_betas_0.9_0.95_WSD_embedding_no_decay",
    }, checkpoint_path)
    metadata.update({
        "steps": args.steps,
        "objective": "shared_causal_next_token_prediction",
        "validation_after": after,
        "collective_loss_delta": after["collective_loss"] - before["collective_loss"],
        "checkpoint": str(checkpoint_path),
    })
    (args.output / "training_report.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(metadata, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=("smoke", "target"), default="smoke")
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--tokenizer-json", type=Path)
    parser.add_argument("--output", type=Path, default=Path("artifacts"))
    parser.add_argument("--steps", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--warmup-steps", type=int, default=2000)
    parser.add_argument("--decay-ratio", type=float, default=0.1)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=1)
    parser.add_argument("--weight-decay", type=float, default=0.1)
    parser.add_argument("--max-grad-norm", type=float, default=1.0)
    parser.add_argument("--log-every", type=int, default=10)
    parser.add_argument("--auxiliary-loss-weight", type=float, default=0.2)
    parser.add_argument("--gradient-checkpointing", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if args.steps < 1 or args.batch_size < 1:
        parser.error("steps and batch-size must be positive.")
    if args.auxiliary_loss_weight < 0:
        parser.error("auxiliary-loss-weight cannot be negative.")
    if args.gradient_accumulation_steps < 1:
        parser.error("gradient-accumulation-steps must be positive.")
    if args.max_grad_norm <= 0:
        parser.error("max-grad-norm must be positive.")
    if not 0.0 < args.decay_ratio <= 1.0:
        parser.error("decay-ratio must be in (0, 1].")
    train(args)


if __name__ == "__main__":
    main()
