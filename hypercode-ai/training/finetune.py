import argparse
import gzip
import hashlib
import json
import random
from pathlib import Path

import torch
from torch.nn import functional as F

from model import HyperInterNetwork
from optimization import build_adamw, wsd_multiplier
from tokenizer import load_tokenizer


def load_instruction_chunks(path, tokenizer, context_length, seed=2026):
    records = []
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            prompt = row.get("prompt")
            completion = row.get("completion")
            if not isinstance(prompt, str) or not isinstance(completion, str):
                raise ValueError(f"Instruction record {line_number} needs prompt and completion strings.")
            if not prompt.strip() or not completion.strip():
                continue
            prompt_ids = tokenizer.encode(
                prompt,
                language=row.get("language"),
                code=False,
                add_special_tokens=False,
            )
            completion_ids = tokenizer.encode(
                completion,
                language=row.get("language"),
                code=row.get("kind") == "code",
                add_special_tokens=False,
            )
            ids = [tokenizer.bos_id, *prompt_ids, *completion_ids, tokenizer.eos_id]
            target_start = len(prompt_ids)
            if len(ids) >= 3:
                records.append((ids, target_start))
    if len(records) < 2:
        raise ValueError("At least two instruction records are required.")

    random.Random(seed).shuffle(records)
    split = max(1, int(len(records) * 0.9))

    def make_chunks(items):
        chunks = []
        for ids, target_start in items:
            for start in range(0, len(ids) - 1, context_length):
                part = ids[start:start + context_length + 1]
                local_target_start = max(0, target_start - start)
                if len(part) < 3 or local_target_start >= len(part) - 1:
                    continue
                chunks.append((part, local_target_start))
        return chunks

    train_chunks = make_chunks(records[:split])
    validation_chunks = make_chunks(records[split:])
    if not train_chunks or not validation_chunks:
        raise ValueError("Not enough assistant-completion tokens for train/validation chunks.")
    return train_chunks, validation_chunks


def make_batch(samples, batch_size, context_length, device):
    inputs = []
    targets = []
    for _ in range(batch_size):
        tokens, target_start = random.choice(samples)
        if len(tokens) > context_length + 1:
            start = random.randrange(0, len(tokens) - context_length)
            part = tokens[start:start + context_length + 1]
            mask_start = max(0, target_start - start)
        else:
            part = list(tokens)
            mask_start = target_start
        input_row = part[:-1]
        target_row = part[1:]
        for index in range(min(mask_start, len(target_row))):
            target_row[index] = -100
        input_row += [0] * (context_length - len(input_row))
        target_row += [-100] * (context_length - len(target_row))
        inputs.append(input_row)
        targets.append(target_row)
    return (
        torch.tensor(inputs, dtype=torch.long, device=device),
        torch.tensor(targets, dtype=torch.long, device=device),
    )


def loss_for(logits, targets):
    return F.cross_entropy(
        logits.reshape(-1, logits.size(-1)),
        targets.reshape(-1),
        ignore_index=-100,
    )


def evaluate(model, samples, batch_size, context_length, device, batches=8, use_bf16=False):
    model.eval()
    losses = []
    with torch.no_grad():
        for _ in range(batches):
            inputs, targets = make_batch(samples, batch_size, context_length, device)
            supervised_tokens_this_step += int((targets != -100).sum().item())
            with torch.autocast(
                device_type=device.type,
                dtype=torch.bfloat16 if use_bf16 else torch.float16,
                enabled=device.type == "cuda",
            ):
                final_logits, auxiliary = model(inputs, return_aux=True)
                total = loss_for(final_logits, targets)
                aux = torch.stack([
                    loss_for(auxiliary[:, index], targets) for index in range(7)
                ]).mean()
            losses.append((total.item(), aux.item()))
    model.train()
    return {
        "collective_loss": sum(item[0] for item in losses) / len(losses),
        "mean_individual_loss": sum(item[1] for item in losses) / len(losses),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--tokenizer-json", type=Path)
    parser.add_argument("--output", type=Path, default=Path("artifacts/sft"))
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--warmup-steps", type=int, default=100)
    parser.add_argument("--decay-ratio", type=float, default=0.1)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=1)
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--max-grad-norm", type=float, default=1.0)
    parser.add_argument("--auxiliary-loss-weight", type=float, default=0.2)
    parser.add_argument("--log-every", type=int, default=20)
    parser.add_argument("--gradient-checkpointing", action="store_true")
    parser.add_argument("--seed", type=int, default=123)
    args = parser.parse_args()
    if args.steps < 1 or args.batch_size < 1 or args.gradient_accumulation_steps < 1:
        parser.error("steps, batch-size and gradient-accumulation-steps must be positive")
    if not 0.0 < args.decay_ratio <= 1.0 or args.max_grad_norm <= 0:
        parser.error("invalid scheduler or gradient clipping configuration")

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    config = dict(checkpoint["config"])
    is_target = (
        config.get("experts") == 7
        and config.get("expert_layers") == 10
        and config.get("expert_width") == 256
        and config.get("fusion_layers") == 20
        and config.get("fusion_width") == 1792
    )
    if is_target and device.type != "cuda":
        raise RuntimeError("The target model requires CUDA for SFT. Refusing to allocate it on CPU.")
    if is_target and not torch.cuda.is_bf16_supported():
        raise RuntimeError("Target SFT requires a CUDA GPU with BF16 support.")
    model = HyperInterNetwork(**config).to(device)
    model.load_state_dict(checkpoint["state_dict"])
    model.set_gradient_checkpointing(args.gradient_checkpointing)
    use_bf16 = device.type == "cuda" and torch.cuda.is_bf16_supported()
    scaler = torch.amp.GradScaler(
        "cuda",
        enabled=device.type == "cuda" and not use_bf16,
    )

    tokenizer = load_tokenizer(args.tokenizer_json)
    if tokenizer.vocab_size != config["vocab_size"]:
        raise ValueError("SFT tokenizer vocabulary does not match the pretrained checkpoint.")
    tokenizer_sha256 = (
        hashlib.sha256(Path(args.tokenizer_json).read_bytes()).hexdigest()
        if args.tokenizer_json else "procedural-byte-v1"
    )
    if checkpoint.get("tokenizer_sha256", "procedural-byte-v1") != tokenizer_sha256:
        raise ValueError("SFT tokenizer fingerprint does not match the pretrained checkpoint.")
    train_samples, validation_samples = load_instruction_chunks(
        args.data,
        tokenizer,
        config["context_length"],
        seed=args.seed,
    )
    optimizer = build_adamw(
        model,
        learning_rate=args.learning_rate,
        weight_decay=args.weight_decay,
        fused=device.type == "cuda",
    )
    args.output.mkdir(parents=True, exist_ok=True)
    before = evaluate(
        model,
        validation_samples,
        args.batch_size,
        config["context_length"],
        device,
        use_bf16=use_bf16,
    )
    effective_warmup_steps = min(args.warmup_steps, max(1, args.steps // 10))
    total_supervised_tokens = 0
    model.train()
    for step in range(1, args.steps + 1):
        for group in optimizer.param_groups:
            group["lr"] = args.learning_rate * wsd_multiplier(
                step, args.steps, effective_warmup_steps, args.decay_ratio
            )
        optimizer.zero_grad(set_to_none=True)
        accumulated_loss = 0.0
        collective_loss_value = 0.0
        supervised_tokens_this_step = 0
        for _ in range(args.gradient_accumulation_steps):
            inputs, targets = make_batch(
                train_samples,
                args.batch_size,
                config["context_length"],
                device,
            )
            supervised_tokens_this_step += int((targets != -100).sum().item())
            with torch.autocast(
                device_type=device.type,
                dtype=torch.bfloat16 if use_bf16 else torch.float16,
                enabled=device.type == "cuda",
            ):
                final_logits, auxiliary = model(inputs, return_aux=True)
                final_loss = loss_for(final_logits, targets)
                auxiliary_loss = torch.stack([
                    loss_for(auxiliary[:, index], targets) for index in range(7)
                ]).mean()
                loss = (
                    final_loss + args.auxiliary_loss_weight * auxiliary_loss
                ) / args.gradient_accumulation_steps
            if not torch.isfinite(loss):
                raise FloatingPointError(f"Non-finite SFT loss at step {step}.")
            accumulated_loss += loss.detach().item()
            collective_loss_value += final_loss.detach().item() / args.gradient_accumulation_steps
            scaler.scale(loss).backward()
        scaler.unscale_(optimizer)
        gradient_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), args.max_grad_norm)
        if not torch.isfinite(gradient_norm):
            raise FloatingPointError(f"Non-finite SFT gradient norm at step {step}.")
        scaler.step(optimizer)
        scaler.update()
        total_supervised_tokens += supervised_tokens_this_step
        if step == 1 or step % args.log_every == 0 or step == args.steps:
            print(
                f"sft_step={step}/{args.steps} total={accumulated_loss:.5f} "
                f"collective={collective_loss_value:.5f} grad_norm={float(gradient_norm):.5f}"
            )

    after = evaluate(
        model,
        validation_samples,
        args.batch_size,
        config["context_length"],
        device,
        use_bf16=use_bf16,
    )
    output_checkpoint = args.output / "hyperinter_sft_checkpoint.pt"
    torch.save({
        "state_dict": model.state_dict(),
        "config": config,
        "training_steps": args.steps,
        "stage": "assistant_completion_supervised_finetuning",
        "base_checkpoint": str(args.checkpoint),
        "optimizer_state_dict": optimizer.state_dict(),
        "tokenizer_sha256": tokenizer_sha256,
        "training_recipe": "SFT_completion_mask_AdamW_WSD_gradient_accumulation",
        "supervised_completion_tokens_seen": total_supervised_tokens,
    }, output_checkpoint)
    report = {
        "device": str(device),
        "bf16": use_bf16,
        "gradient_checkpointing": args.gradient_checkpointing,
        "stage": "assistant_completion_supervised_finetuning",
        "train_chunks": len(train_samples),
        "validation_chunks": len(validation_samples),
        "steps": args.steps,
        "supervised_completion_tokens_seen": total_supervised_tokens,
        "effective_batch_size": args.batch_size * args.gradient_accumulation_steps,
        "gradient_accumulation_steps": args.gradient_accumulation_steps,
        "effective_warmup_steps": effective_warmup_steps,
        "tokenizer_sha256": tokenizer_sha256,
        "validation_before": before,
        "validation_after": after,
        "collective_loss_delta": after["collective_loss"] - before["collective_loss"],
        "checkpoint": str(output_checkpoint),
        "note": "Only assistant completion tokens contribute to the loss; prompt tokens are masked.",
    }
    (args.output / "sft_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
