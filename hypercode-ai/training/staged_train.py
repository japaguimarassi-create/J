import argparse
import hashlib
import json
import math
import os
import random
from pathlib import Path

import torch

from foundation import initialize_hyper_from_foundation
from model import HyperInterNetwork, smoke_config, target_config
from optimization import build_adamw, capture_rng_state, restore_rng_state, wsd_multiplier
from tokenizer import load_tokenizer
from train import language_model_loss, make_batch, read_corpus


STAGES = ("expert", "core", "communication", "joint")


def configure_stage(model, stage, expert_index=None):
    for parameter in model.parameters():
        parameter.requires_grad_(False)

    if stage == "expert":
        if expert_index is None or not 0 <= expert_index < 7:
            raise ValueError("The expert stage requires an expert index from 0 to 6.")
        if expert_index == 0:
            model.token_embedding.requires_grad_(True)
            model.position_embedding.requires_grad_(True)
        for module in (
            model.experts[expert_index],
            model.expert_norms[expert_index],
        ):
            for parameter in module.parameters():
                parameter.requires_grad_(True)
        model.expert_head_biases[expert_index].requires_grad_(True)
    elif stage == "core":
        model.fusion_positions.requires_grad_(True)
        for module in (
            model.fusion_blocks,
            model.fusion_norm,
            model.output_projection,
            model.output_norm,
        ):
            for parameter in module.parameters():
                parameter.requires_grad_(True)
        model.output_bias.requires_grad_(True)
    elif stage == "communication":
        for module in model.communication:
            for parameter in module.parameters():
                parameter.requires_grad_(True)
    elif stage == "joint":
        for parameter in model.parameters():
            parameter.requires_grad_(True)
    else:
        raise ValueError(f"Unknown training stage: {stage}")

    parameters = [parameter for parameter in model.parameters() if parameter.requires_grad]
    if not parameters:
        raise RuntimeError(f"Stage {stage} has no trainable parameters.")
    return parameters


def validate_stage_prerequisites(stage, expert_index, completed_experts, completed_stages):
    if stage == "expert":
        if expert_index is None or not 0 <= expert_index < 7:
            raise ValueError("The expert stage requires expert index 0 through 6.")
        if "core" in completed_stages:
            raise ValueError("Expert training is closed after the core stage.")
        missing = set(range(expert_index)) - set(completed_experts)
        if missing:
            raise ValueError(f"Train expert networks in order; missing {sorted(missing)}.")
        if expert_index in completed_experts:
            raise ValueError(f"Expert {expert_index} is already marked complete.")
    elif stage == "core":
        if set(completed_experts) != set(range(7)):
            raise ValueError("Core training requires all seven expert checkpoints.")
        if "core" in completed_stages:
            raise ValueError("Core stage is already complete.")
    elif stage == "communication":
        if "core" not in completed_stages:
            raise ValueError("Communication training requires a completed core.")
        if "communication" in completed_stages:
            raise ValueError("Communication stage is already complete.")
    elif stage == "joint":
        if "communication" not in completed_stages:
            raise ValueError("Joint training requires completed communication.")
        if "joint" in completed_stages:
            raise ValueError("Joint stage is already complete.")
    else:
        raise ValueError(f"Unknown stage: {stage}")


def stage_logits(model, inputs, stage, expert_index):
    if stage == "expert":
        return model.forward_expert(inputs, expert_index)
    if stage == "core":
        return model(inputs, use_communication=False)
    return model(inputs, use_communication=True)


def stage_loss(model, inputs, targets, stage, expert_index, auxiliary_weight):
    if stage != "joint":
        return language_model_loss(stage_logits(model, inputs, stage, expert_index), targets)
    final_logits, expert_logits = model(inputs, return_aux=True, use_communication=True)
    collective_loss = language_model_loss(final_logits, targets)
    individual_losses = [
        language_model_loss(expert_logits[:, index], targets)
        for index in range(7)
    ]
    return collective_loss + auxiliary_weight * torch.stack(individual_losses).mean()


def evaluate_stage(model, samples, args, device, use_bf16):
    model.eval()
    losses = []
    random_state = random.getstate()
    random.seed(args.seed + 100003)
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
                logits = stage_logits(model, inputs, args.stage, args.expert_index)
                loss = language_model_loss(logits, targets)
            losses.append(loss.item())
    random.setstate(random_state)
    model.train()
    mean_loss = sum(losses) / len(losses)
    return {"loss": mean_loss, "batches": len(losses)}



def evaluate_all_experts(model, samples, args, device, use_bf16):
    model.eval()
    losses = [0.0] * 7
    random_state = random.getstate()
    random.seed(args.seed + 200003)
    with torch.no_grad():
        for _ in range(args.validation_batches):
            inputs, targets = make_batch(
                samples,
                args.batch_size,
                model.context_length,
                device,
            )
            for expert_index in range(7):
                with torch.autocast(
                    device_type=device.type,
                    dtype=torch.bfloat16 if use_bf16 else torch.float16,
                    enabled=device.type == "cuda",
                ):
                    logits = model.forward_expert(inputs, expert_index)
                    loss = language_model_loss(logits, targets)
                losses[expert_index] += loss.item()
    random.setstate(random_state)
    model.train()
    per_network = [value / args.validation_batches for value in losses]
    return {
        "per_network_loss": per_network,
        "mean_loss": sum(per_network) / len(per_network),
    }


def validation_gate_passes(before, after, tolerance=0.0):
    return (
        math.isfinite(before)
        and math.isfinite(after)
        and after <= before + tolerance
    )


def atomic_save(payload, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    torch.save(payload, temporary)
    os.replace(temporary, path)


def checkpoint_payload(model, optimizer, config, tokenizer_sha256, completed_experts, completed_stages,
                       stage, expert_index, current_step, report, in_progress):
    return {
        "state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "config": config,
        "tokenizer_sha256": tokenizer_sha256,
        "rng_state": capture_rng_state(),
        "completed_experts": sorted(completed_experts),
        "completed_stages": sorted(completed_stages),
        "in_progress_stage": stage if in_progress else None,
        "in_progress_expert_index": expert_index if in_progress else None,
        "steps_completed_in_stage": current_step if in_progress else 0,
        "last_stage_report": report,
        "training_method": "progressive_component_training_then_full_joint_finetuning",
        "all_seven_networks_are_universal": True,
        "same_corpus_for_all_experts": True,
    }


def expected_output_path(args):
    label = f"expert_{args.expert_index + 1:02d}" if args.stage == "expert" else args.stage
    return args.output / label / f"hyperinter_{label}.pt"


def train(args):
    if args.steps < 1 or args.batch_size < 1 or args.validation_batches < 1 or args.save_every < 1:
        raise ValueError("steps, batch-size, validation-batches and save-every must be positive.")
    if args.stage == "expert" and args.expert_index is None:
        raise ValueError("--expert-index is required with --stage expert.")
    if args.base_checkpoint is not None and args.checkpoint is not None:
        raise ValueError("Use --base-checkpoint only for initialization, not when resuming a fusion checkpoint.")
    if args.stage != "expert" and args.expert_index is not None:
        raise ValueError("--expert-index is only valid with --stage expert.")

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    config = target_config() if args.profile == "target" else smoke_config()
    if args.profile == "target" and args.tokenizer_json is None:
        raise RuntimeError("Target training requires a trained BPE tokenizer. Run train_bpe_tokenizer.py first.")
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
        raise RuntimeError("The target architecture requires CUDA; no reduced CPU fallback is allowed.")
    if args.profile == "target" and not torch.cuda.is_bf16_supported():
        raise RuntimeError("Target training requires a CUDA GPU with BF16 support.")

    loaded = None
    if args.checkpoint:
        loaded = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
        if loaded.get("config") != config:
            raise ValueError("Checkpoint architecture does not match the selected profile.")
        if loaded.get("tokenizer_sha256", "procedural-byte-v1") != tokenizer_sha256:
            raise ValueError("Checkpoint tokenizer fingerprint does not match the selected tokenizer.")
        model = HyperInterNetwork(**config)
        model.load_state_dict(loaded["state_dict"])
        completed_experts = set(loaded.get("completed_experts", []))
        completed_stages = set(loaded.get("completed_stages", []))
    else:
        if args.stage != "expert" or args.expert_index != 0:
            raise ValueError("Start with expert index 0. Later stages require their preceding checkpoint.")
        if args.profile == "target" and args.base_checkpoint is None:
            raise RuntimeError("Target fusion requires a trained universal foundation checkpoint.")
        if args.base_checkpoint is not None:
            base_payload = torch.load(args.base_checkpoint, map_location="cpu", weights_only=False)
            if base_payload.get("config") != config:
                raise ValueError("Foundation architecture does not match the selected fusion profile.")
            if base_payload.get("tokenizer_sha256") != tokenizer_sha256:
                raise ValueError("Foundation and fusion tokenizer fingerprints do not match.")
        model = HyperInterNetwork(**config)
        if args.base_checkpoint is not None:
            model = initialize_hyper_from_foundation(model, base_payload, tokenizer_sha256)
        completed_experts = set()
        completed_stages = set()

    in_progress = loaded.get("in_progress_stage") if loaded else None
    in_progress_expert = loaded.get("in_progress_expert_index") if loaded else None
    if in_progress:
        if in_progress != args.stage or in_progress_expert != args.expert_index:
            raise ValueError(f"Checkpoint is unfinished at {in_progress}; resume that exact stage first.")
    else:
        validate_stage_prerequisites(
            args.stage,
            args.expert_index,
            completed_experts,
            completed_stages,
        )

    trainable = configure_stage(model, args.stage, args.expert_index)
    model = model.to(device)
    trainable = [parameter for parameter in model.parameters() if parameter.requires_grad]
    model.set_gradient_checkpointing(args.gradient_checkpointing or args.profile == "target")
    optimizer = build_adamw(
        model,
        learning_rate=args.learning_rate,
        weight_decay=args.weight_decay,
        fused=device.type == "cuda",
    )
    already_completed_steps = 0
    if in_progress:
        if loaded.get("optimizer_state_dict"):
            optimizer.load_state_dict(loaded["optimizer_state_dict"])
        restore_rng_state(loaded.get("rng_state"))
        already_completed_steps = int(loaded.get("steps_completed_in_stage", 0))
        if already_completed_steps >= args.steps:
            raise ValueError("Checkpoint already reached the requested total number of steps.")
    else:
        stage_seed = args.seed + (
            1009 * args.expert_index if args.stage == "expert"
            else {"core": 20011, "communication": 30011, "joint": 40009}[args.stage]
        )
        random.seed(stage_seed)
        torch.manual_seed(stage_seed)
        if device.type == "cuda":
            torch.cuda.manual_seed_all(stage_seed)

    use_bf16 = device.type == "cuda" and torch.cuda.is_bf16_supported()
    scaler = torch.amp.GradScaler(
        "cuda",
        enabled=device.type == "cuda" and not use_bf16,
    )
    output_path = expected_output_path(args)
    stage_label = f"expert_{args.expert_index + 1:02d}" if args.stage == "expert" else args.stage

    validation_before = evaluate_stage(
        model,
        validation_samples,
        args,
        device,
        use_bf16,
    )
    report = {
        "stage": stage_label,
        "expert_index": args.expert_index,
        "profile": args.profile,
        "device": str(device),
        "trainable_parameters": sum(parameter.numel() for parameter in trainable),
        "steps_requested": args.steps,
        "steps_resumed_from": already_completed_steps,
        "validation_before": validation_before,
        "same_universal_corpus_for_all_seven": True,
        "tokenizer_vocab_size": tokenizer.vocab_size,
        "tokenizer_sha256": tokenizer_sha256,
        "effective_batch_size": args.batch_size * args.gradient_accumulation_steps,
        "gradient_accumulation_steps": args.gradient_accumulation_steps,
        "scheduler": "warmup_stable_decay",
        "decay_ratio": args.decay_ratio,
    }
    print(json.dumps(report, ensure_ascii=False))

    effective_warmup_steps = min(args.warmup_steps, max(1, args.steps // 10))
    report["effective_warmup_steps"] = effective_warmup_steps

    model.train()
    for step in range(already_completed_steps + 1, args.steps + 1):
        multiplier = wsd_multiplier(step, args.steps, effective_warmup_steps, args.decay_ratio)
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
                micro_loss = stage_loss(
                    model,
                    inputs,
                    targets,
                    args.stage,
                    args.expert_index,
                    args.auxiliary_loss_weight,
                ) / args.gradient_accumulation_steps
            if not torch.isfinite(micro_loss):
                raise FloatingPointError(f"Non-finite loss at {stage_label} step {step}.")
            accumulated_loss += micro_loss.detach().item()
            scaler.scale(micro_loss).backward()

        scaler.unscale_(optimizer)
        gradient_norm = torch.nn.utils.clip_grad_norm_(trainable, args.max_grad_norm)
        if not torch.isfinite(gradient_norm):
            raise FloatingPointError(f"Non-finite gradient norm at {stage_label} step {step}.")
        scaler.step(optimizer)
        scaler.update()

        if step == 1 or step % args.log_every == 0 or step == args.steps:
            print(
                f"stage={stage_label} step={step}/{args.steps} "
                f"loss={accumulated_loss:.6f} lr={optimizer.param_groups[0]['lr']:.8g} "
                f"grad_norm={float(gradient_norm):.5f}"
            )

        if step % args.save_every == 0 and step < args.steps:
            payload = checkpoint_payload(
                model,
                optimizer,
                config,
                tokenizer_sha256,
                completed_experts,
                completed_stages,
                args.stage,
                args.expert_index,
                step,
                report,
                True,
            )
            atomic_save(payload, output_path)

    validation_after = evaluate_stage(
        model,
        validation_samples,
        args,
        device,
        use_bf16,
    )
    if not math.isfinite(validation_after["loss"]):
        raise FloatingPointError(f"Non-finite validation loss after {stage_label}.")

    report.update({
        "validation_after": validation_after,
        "validation_delta": validation_after["loss"] - validation_before["loss"],
        "validation_gate_passed": validation_gate_passes(
            validation_before["loss"],
            validation_after["loss"],
            args.validation_tolerance,
        ),
    })

    if args.stage == "expert" and args.expert_index == 6:
        report["all_seven_independent_outputs"] = evaluate_all_experts(
            model,
            validation_samples,
            args,
            device,
            use_bf16,
        )

    if not report["validation_gate_passed"] and not args.allow_validation_regression:
        report["status"] = "validation_gate_failed"
        report["next_required_step"] = f"continue_{stage_label}"
        payload = checkpoint_payload(
            model,
            optimizer,
            config,
            tokenizer_sha256,
            completed_experts,
            completed_stages,
            args.stage,
            args.expert_index,
            args.steps,
            report,
            True,
        )
        atomic_save(payload, output_path)
        report_path = output_path.with_suffix(".report.json")
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        raise RuntimeError(
            f"{stage_label} failed the validation gate. The in-progress checkpoint was saved; "
            "increase --steps and resume the same stage, or explicitly allow the regression for a smoke test."
        )

    if args.stage == "expert":
        completed_experts.add(args.expert_index)
    else:
        completed_stages.add(args.stage)

    report.update({
        "status": "completed",
        "next_required_step": (
            f"expert_{args.expert_index + 2:02d}" if args.stage == "expert" and args.expert_index < 6
            else "core" if args.stage == "expert"
            else "communication" if args.stage == "core"
            else "joint" if args.stage == "communication"
            else "general_evaluation"
        ),
    })
    payload = checkpoint_payload(
        model,
        optimizer,
        config,
        tokenizer_sha256,
        completed_experts,
        completed_stages,
        args.stage,
        args.expert_index,
        args.steps,
        report,
        False,
    )
    atomic_save(payload, output_path)
    report_path = output_path.with_suffix(".report.json")
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    print(f"checkpoint={output_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=("smoke", "target"), default="smoke")
    parser.add_argument("--stage", choices=STAGES, required=True)
    parser.add_argument("--expert-index", type=int)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--tokenizer-json", type=Path)
    parser.add_argument("--base-checkpoint", type=Path)
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--output", type=Path, default=Path("artifacts/staged"))
    parser.add_argument("--steps", type=int, default=1000)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--warmup-steps", type=int, default=2000)
    parser.add_argument("--decay-ratio", type=float, default=0.1)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=1)
    parser.add_argument("--weight-decay", type=float, default=0.1)
    parser.add_argument("--auxiliary-loss-weight", type=float, default=0.2)
    parser.add_argument("--max-grad-norm", type=float, default=1.0)
    parser.add_argument("--log-every", type=int, default=50)
    parser.add_argument("--save-every", type=int, default=250)
    parser.add_argument("--validation-batches", type=int, default=4)
    parser.add_argument("--validation-tolerance", type=float, default=0.0)
    parser.add_argument("--allow-validation-regression", action="store_true")
    parser.add_argument("--gradient-checkpointing", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if args.expert_index is not None and not 0 <= args.expert_index < 7:
        parser.error("expert-index must be between 0 and 6")
    if args.gradient_accumulation_steps < 1:
        parser.error("gradient-accumulation-steps must be positive")
    if not 0.0 < args.decay_ratio <= 1.0:
        parser.error("decay-ratio must be in (0, 1]")
    train(args)


if __name__ == "__main__":
    main()
