import argparse
import hashlib
import json
import math
import os
import random
from pathlib import Path

import torch
from torch import nn
from torch.nn import functional as F
from torch.utils.checkpoint import checkpoint

from model import CausalBlock, smoke_config, target_config
from optimization import build_adamw, capture_rng_state, restore_rng_state, wsd_multiplier
from tokenizer import load_tokenizer
from train import language_model_loss, make_batch, read_corpus


class UniversalFoundationModel(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.vocab_size = config["vocab_size"]
        self.context_length = config["context_length"]
        self.width = config["expert_width"]
        self.gradient_checkpointing = False
        self.token_embedding = nn.Embedding(self.vocab_size, self.width)
        self.position_embedding = nn.Parameter(
            torch.zeros(1, self.context_length, self.width)
        )
        self.network_identity = nn.Parameter(torch.empty(1, 1, self.width))
        nn.init.normal_(self.position_embedding, mean=0.0, std=0.02)
        nn.init.normal_(self.network_identity, mean=0.0, std=0.02)
        self.blocks = nn.ModuleList([
            CausalBlock(
                self.width,
                config["expert_heads"],
                config["expert_ff"],
                config["dropout"],
            )
            for _ in range(config["expert_layers"])
        ])
        self.norm = nn.LayerNorm(self.width)
        self.output_bias = nn.Parameter(torch.zeros(self.vocab_size))

    def set_gradient_checkpointing(self, enabled=True):
        self.gradient_checkpointing = bool(enabled)

    def forward(self, input_ids):
        if input_ids.ndim != 2:
            raise ValueError("input_ids must have shape [batch, sequence].")
        sequence = input_ids.size(1)
        if sequence > self.context_length:
            raise ValueError("Input sequence exceeds configured context length.")
        hidden = (
            self.token_embedding(input_ids)
            + self.position_embedding[:, :sequence]
            + self.network_identity
        )
        for block in self.blocks:
            if self.gradient_checkpointing and self.training:
                hidden = checkpoint(block, hidden, use_reentrant=False)
            else:
                hidden = block(hidden)
        hidden = self.norm(hidden)
        return F.linear(hidden, self.token_embedding.weight, self.output_bias)


def initialize_hyper_from_foundation(model, payload, tokenizer_sha256, target_config):
    if payload.get("tokenizer_sha256") != tokenizer_sha256:
        raise ValueError("Foundation checkpoint tokenizer fingerprint does not match.")
    if payload.get("in_progress"):
        raise ValueError("An unfinished foundation checkpoint cannot initialize the seven-network model.")
    base_config = payload.get("config", {})
    fields = (
        "vocab_size",
        "context_length",
        "expert_layers",
        "expert_width",
        "expert_heads",
        "expert_ff",
        "dropout",
    )
    for field in fields:
        if base_config.get(field) != target_config.get(field):
            raise ValueError(f"Foundation configuration mismatch for {field}.")
    base = UniversalFoundationModel(base_config)
    base.load_state_dict(payload["state_dict"], strict=True)
    if (
        base.vocab_size != model.vocab_size
        or base.context_length != model.context_length
        or len(base.blocks) != len(model.experts[0])
        or base.width != model.expert_width
    ):
        raise ValueError("Foundation architecture is incompatible with the seven-network model.")

    with torch.no_grad():
        model.token_embedding.weight.copy_(base.token_embedding.weight)
        model.position_embedding.copy_(base.position_embedding)
        for index in range(model.expert_count):
            for target_block, base_block in zip(model.experts[index], base.blocks):
                target_block.load_state_dict(base_block.state_dict(), strict=True)
            model.expert_norms[index].load_state_dict(base.norm.state_dict(), strict=True)
            model.expert_head_biases[index].copy_(base.output_bias)
        identity = base.network_identity.unsqueeze(1).expand_as(model.expert_identity)
        noise = torch.randn_like(model.expert_identity) * 0.002
        model.expert_identity.copy_(identity + noise)
    return model


def evaluate(model, samples, args, device, use_bf16):
    model.eval()
    random_state = random.getstate()
    random.seed(args.seed + 100003)
    losses = []
    with torch.no_grad():
        for _ in range(args.validation_batches):
            inputs, targets = make_batch(
                samples,
                args.batch_size,
                model.context_length,
                device,
            )
            with torch.autocast(
                device_type=device.type,
                dtype=torch.bfloat16 if use_bf16 else torch.float16,
                enabled=device.type == "cuda",
            ):
                logits = model(inputs)
                losses.append(language_model_loss(logits, targets).item())
    random.setstate(random_state)
    model.train()
    return {"loss": sum(losses) / len(losses), "batches": len(losses)}


def atomic_save(payload, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    torch.save(payload, temporary)
    os.replace(temporary, path)


def train(args):
    if min(args.steps, args.batch_size, args.gradient_accumulation_steps,
           args.validation_batches, args.save_every) < 1:
        raise ValueError("Training, batch, accumulation, validation and save values must be positive.")
    if args.max_grad_norm <= 0:
        raise ValueError("max-grad-norm must be positive.")
    if not 0.0 < args.decay_ratio <= 1.0:
        raise ValueError("decay-ratio must be in (0, 1].")

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    config = target_config() if args.profile == "target" else smoke_config()
    if args.profile == "target" and args.tokenizer_json is None:
        raise RuntimeError("Target foundation training requires a trained BPE tokenizer.")
    tokenizer = load_tokenizer(args.tokenizer_json)
    config["vocab_size"] = tokenizer.vocab_size
    tokenizer_sha256 = (
        hashlib.sha256(Path(args.tokenizer_json).read_bytes()).hexdigest()
        if args.tokenizer_json else "procedural-byte-v1"
    )
    train_samples, validation_samples = read_corpus(
        args.data,
        tokenizer,
        config["context_length"],
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if args.profile == "target" and device.type != "cuda":
        raise RuntimeError("Target foundation training requires CUDA; refusing a reduced CPU substitute.")
    if args.profile == "target" and not torch.cuda.is_bf16_supported():
        raise RuntimeError("Target foundation training requires CUDA BF16 support.")

    model = UniversalFoundationModel(config)
    loaded = None
    if args.checkpoint:
        loaded = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
        if loaded.get("config") != config:
            raise ValueError("Foundation checkpoint architecture does not match.")
        if loaded.get("tokenizer_sha256") != tokenizer_sha256:
            raise ValueError("Foundation checkpoint tokenizer fingerprint does not match.")
        model.load_state_dict(loaded["state_dict"], strict=True)
    model = model.to(device)
    model.set_gradient_checkpointing(args.gradient_checkpointing or args.profile == "target")
    optimizer = build_adamw(
        model,
        learning_rate=args.learning_rate,
        weight_decay=args.weight_decay,
        fused=device.type == "cuda",
    )
    completed_steps = 0
    if loaded:
        if loaded.get("optimizer_state_dict"):
            optimizer.load_state_dict(loaded["optimizer_state_dict"])
        restore_rng_state(loaded.get("rng_state"))
        completed_steps = int(loaded.get("steps_completed", 0))
    if completed_steps >= args.steps:
        raise ValueError("Foundation checkpoint already reached the requested step count.")

    use_bf16 = device.type == "cuda" and torch.cuda.is_bf16_supported()
    scaler = torch.amp.GradScaler(
        "cuda",
        enabled=device.type == "cuda" and not use_bf16,
    )
    effective_warmup = min(args.warmup_steps, max(1, args.steps // 10))
    before = evaluate(model, validation_samples, args, device, use_bf16)
    report = {
        "stage": "universal_foundation_pretraining",
        "profile": args.profile,
        "device": str(device),
        "parameters": sum(parameter.numel() for parameter in model.parameters()),
        "train_chunks": len(train_samples),
        "validation_chunks": len(validation_samples),
        "steps_requested": args.steps,
        "steps_resumed_from": completed_steps,
        "effective_batch_size": args.batch_size * args.gradient_accumulation_steps,
        "gradient_accumulation_steps": args.gradient_accumulation_steps,
        "tokenizer_vocab_size": tokenizer.vocab_size,
        "tokenizer_sha256": tokenizer_sha256,
        "scheduler": "warmup_stable_decay",
        "effective_warmup_steps": effective_warmup,
        "validation_before": before,
    }
    print(json.dumps(report, ensure_ascii=False))

    model.train()
    output_path = args.output / "hyperinter_foundation.pt"
    for step in range(completed_steps + 1, args.steps + 1):
        multiplier = wsd_multiplier(step, args.steps, effective_warmup, args.decay_ratio)
        for group in optimizer.param_groups:
            group["lr"] = args.learning_rate * multiplier
        optimizer.zero_grad(set_to_none=True)
        accumulated_loss = 0.0
        for _ in range(args.gradient_accumulation_steps):
            inputs, targets = make_batch(
                train_samples,
                args.batch_size,
                model.context_length,
                device,
            )
            with torch.autocast(
                device_type=device.type,
                dtype=torch.bfloat16 if use_bf16 else torch.float16,
                enabled=device.type == "cuda",
            ):
                loss = language_model_loss(model(inputs), targets)
                loss = loss / args.gradient_accumulation_steps
            if not torch.isfinite(loss):
                raise FloatingPointError(f"Non-finite foundation loss at step {step}.")
            accumulated_loss += loss.detach().item()
            scaler.scale(loss).backward()
        scaler.unscale_(optimizer)
        gradient_norm = torch.nn.utils.clip_grad_norm_(
            model.parameters(),
            args.max_grad_norm,
        )
        if not torch.isfinite(gradient_norm):
            raise FloatingPointError(f"Non-finite foundation gradient at step {step}.")
        scaler.step(optimizer)
        scaler.update()
        if step == 1 or step % args.log_every == 0 or step == args.steps:
            print(
                f"foundation_step={step}/{args.steps} loss={accumulated_loss:.6f} "
                f"lr={optimizer.param_groups[0]['lr']:.8g} grad_norm={float(gradient_norm):.5f}"
            )
        if step % args.save_every == 0 and step < args.steps:
            atomic_save({
                "state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "config": config,
                "tokenizer_sha256": tokenizer_sha256,
                "rng_state": capture_rng_state(),
                "steps_completed": step,
                "in_progress": True,
                "training_recipe": "causal_lm_adamw_wsd_bf16_gradient_accumulation",
            }, output_path)

    after = evaluate(model, validation_samples, args, device, use_bf16)
    report["validation_after"] = after
    report["validation_delta"] = after["loss"] - before["loss"]
    report["validation_gate_passed"] = (
        math.isfinite(after["loss"])
        and after["loss"] <= before["loss"] + args.validation_tolerance
    )
    if not report["validation_gate_passed"] and not args.allow_validation_regression:
        report["status"] = "validation_gate_failed"
        atomic_save({
            "state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "config": config,
            "tokenizer_sha256": tokenizer_sha256,
            "rng_state": capture_rng_state(),
            "steps_completed": args.steps,
            "in_progress": True,
            "last_report": report,
        }, output_path)
        raise RuntimeError("Foundation validation regressed; checkpoint saved and promotion blocked.")

    report["status"] = "completed"
    atomic_save({
        "state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "config": config,
        "tokenizer_sha256": tokenizer_sha256,
        "rng_state": capture_rng_state(),
        "steps_completed": args.steps,
        "in_progress": False,
        "training_recipe": "causal_lm_adamw_wsd_bf16_gradient_accumulation",
        "report": report,
    }, output_path)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "foundation_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))
    print(f"foundation_checkpoint={output_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=("smoke", "target"), default="smoke")
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--tokenizer-json", type=Path)
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--output", type=Path, default=Path("artifacts/foundation"))
    parser.add_argument("--steps", type=int, default=1000)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=1)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--warmup-steps", type=int, default=2000)
    parser.add_argument("--decay-ratio", type=float, default=0.1)
    parser.add_argument("--weight-decay", type=float, default=0.1)
    parser.add_argument("--max-grad-norm", type=float, default=1.0)
    parser.add_argument("--validation-batches", type=int, default=4)
    parser.add_argument("--validation-tolerance", type=float, default=0.0)
    parser.add_argument("--allow-validation-regression", action="store_true")
    parser.add_argument("--save-every", type=int, default=250)
    parser.add_argument("--log-every", type=int, default=50)
    parser.add_argument("--gradient-checkpointing", action="store_true")
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()
    train(args)


if __name__ == "__main__":
    main()
