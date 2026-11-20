import argparse
import gzip
import json
import random
from pathlib import Path

import torch
from torch.nn import functional as F

from model import HyperInterNetwork
from tokenizer import ProceduralTokenizer, VOCAB_SIZE


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
            ids = tokenizer.encode(
                prompt + completion,
                language=row.get("language"),
                code=row.get("kind") == "code",
            )
            target_start = len(prompt.encode("utf-8"))
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
    parser.add_argument("--output", type=Path, default=Path("artifacts/sft"))
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--log-every", type=int, default=20)
    parser.add_argument("--gradient-checkpointing", action="store_true")
    parser.add_argument("--seed", type=int, default=123)
    args = parser.parse_args()
    if args.steps < 1 or args.batch_size < 1:
        parser.error("steps and batch-size must be positive")

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    config = dict(checkpoint["config"])
    config["vocab_size"] = VOCAB_SIZE
    is_target = (
        config.get("experts") == 7
        and config.get("expert_layers") == 10
        and config.get("expert_width") == 256
        and config.get("fusion_layers") == 20
        and config.get("fusion_width") == 1792
    )
    if is_target and device.type != "cuda":
        raise RuntimeError("The target model requires CUDA for SFT. Refusing to allocate it on CPU.")
    model = HyperInterNetwork(**config).to(device)
    model.load_state_dict(checkpoint["state_dict"])
    model.set_gradient_checkpointing(args.gradient_checkpointing)
    use_bf16 = device.type == "cuda" and torch.cuda.is_bf16_supported()
    scaler = torch.amp.GradScaler(
        "cuda",
        enabled=device.type == "cuda" and not use_bf16,
    )

    tokenizer = ProceduralTokenizer()
    train_samples, validation_samples = load_instruction_chunks(
        args.data,
        tokenizer,
        config["context_length"],
        seed=args.seed,
    )
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=args.learning_rate,
        betas=(0.9, 0.95),
        weight_decay=0.01,
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
    model.train()
    for step in range(1, args.steps + 1):
        inputs, targets = make_batch(
            train_samples,
            args.batch_size,
            config["context_length"],
            device,
        )
        optimizer.zero_grad(set_to_none=True)
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
            loss = final_loss + 0.2 * auxiliary_loss
        scaler.scale(loss).backward()
        scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        scaler.step(optimizer)
        scaler.update()
        if step == 1 or step % args.log_every == 0 or step == args.steps:
            print(
                f"sft_step={step}/{args.steps} "
                f"total={loss.item():.5f} collective={final_loss.item():.5f}"
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
    }, output_checkpoint)
    report = {
        "device": str(device),
        "bf16": use_bf16,
        "gradient_checkpointing": args.gradient_checkpointing,
        "stage": "assistant_completion_supervised_finetuning",
        "train_chunks": len(train_samples),
        "validation_chunks": len(validation_samples),
        "steps": args.steps,
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
