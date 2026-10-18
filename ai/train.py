import argparse
import json
import math
import os
import random
import time
from contextlib import nullcontext
from functools import partial
from pathlib import Path

import numpy as np
import torch
import torch.distributed as dist
from torch.nn import functional as F

from ai.config import ModelConfig, estimate_parameters, tiny_config
from ai.model import KoworkLM, TransformerBlock
from ai.session_mesh import SessionMeshPlan


def setup_distributed():
    world_size = int(os.environ.get("WORLD_SIZE", "1"))
    local_rank = int(os.environ.get("LOCAL_RANK", "0"))
    if world_size > 1 and not dist.is_initialized():
        dist.init_process_group("nccl" if torch.cuda.is_available() else "gloo")
    return world_size, local_rank, dist.get_rank() if dist.is_initialized() else 0


def initialize_meta_module(module, device, config):
    module.to_empty(device=device, recurse=False)
    for name, parameter in module.named_parameters(recurse=False):
        if name == "bias":
            torch.nn.init.zeros_(parameter)
        elif parameter.ndim == 1:
            torch.nn.init.ones_(parameter)
        else:
            std = 0.02 / math.sqrt(2 * config.num_layers) if parameter.shape[0] == config.hidden_size else 0.02
            torch.nn.init.normal_(parameter, mean=0.0, std=std)


def create_model(config, device, distributed):
    if not distributed:
        return KoworkLM(config).to(device)
    if device.type != "cuda":
        raise RuntimeError("Distributed 10B training requires CUDA devices.")
    from torch.distributed.fsdp import FullyShardedDataParallel as FSDP
    from torch.distributed.fsdp import MixedPrecision, ShardingStrategy
    from torch.distributed.fsdp.wrap import transformer_auto_wrap_policy

    model = KoworkLM(config, device="meta")
    initializer = partial(initialize_meta_module, device=device, config=config)
    precision = MixedPrecision(param_dtype=torch.bfloat16, reduce_dtype=torch.float32, buffer_dtype=torch.bfloat16)
    return FSDP(
        model,
        auto_wrap_policy=partial(transformer_auto_wrap_policy, transformer_layer_cls={TransformerBlock}),
        sharding_strategy=ShardingStrategy.FULL_SHARD,
        mixed_precision=precision,
        device_id=device,
        param_init_fn=initializer,
        use_orig_params=True,
        limit_all_gathers=True,
    )


def load_tokens(path, vocab_size, sequence_length, required=True):
    token_path = Path(path)
    if not token_path.is_file():
        if required:
            raise SystemExit("Missing token corpus: {}. Run ai/prepare_data.py first.".format(token_path))
        return None
    if token_path.stat().st_size % 2:
        raise SystemExit("Token stream must contain uint16 little-endian values: {}".format(token_path))
    tokens = np.memmap(token_path, dtype="<u2", mode="r")
    if len(tokens) <= sequence_length + 1:
        if required:
            raise SystemExit("Token corpus is too short for sequence length {}: {}".format(sequence_length, token_path))
        return None
    if int(tokens.max()) >= vocab_size:
        raise SystemExit("Token stream has IDs outside the configured vocabulary: {}".format(token_path))
    return tokens


def sample_training_batch(tokens, sequence_length, mesh_ids, mesh_count, rngs, device):
    token_count = len(tokens)
    global_high = token_count - sequence_length
    starts = []
    for mesh_id in mesh_ids:
        shard_low = mesh_id * token_count // mesh_count
        shard_high = (mesh_id + 1) * token_count // mesh_count
        low = min(shard_low, global_high - 1)
        high = min(shard_high - sequence_length, global_high)
        if high <= low:
            low = 0
            high = global_high
        starts.append(int(rngs[mesh_id].integers(low, high)))
    batch = np.stack([tokens[start:start + sequence_length + 1] for start in starts]).astype(np.int64)
    return torch.as_tensor(batch, device=device)


def evaluate(model, tokens, config, sequence_length, batch_size, batches, device, rank, world_size, seed):
    if tokens is None:
        return None
    was_training = model.training
    model.eval()
    rng = np.random.default_rng(seed + rank * 1_000_003)
    loss_sum = 0.0
    batch_count = 0
    with torch.inference_mode():
        for _ in range(batches):
            starts = rng.integers(0, len(tokens) - sequence_length, size=batch_size)
            values = np.stack([tokens[int(start):int(start) + sequence_length + 1] for start in starts]).astype(np.int64)
            batch = torch.as_tensor(values, device=device)
            context = torch.autocast("cuda", dtype=torch.bfloat16) if device.type == "cuda" else nullcontext()
            with context:
                logits = model(batch[:, :-1])
                loss = F.cross_entropy(logits.float().reshape(-1, config.vocab_size), batch[:, 1:].reshape(-1))
            loss_sum += float(loss.detach().cpu())
            batch_count += 1
    if world_size > 1:
        stats = torch.tensor([loss_sum, batch_count], dtype=torch.float64, device=device)
        dist.all_reduce(stats, op=dist.ReduceOp.SUM)
        loss_sum, batch_count = float(stats[0].item()), int(stats[1].item())
    if was_training:
        model.train()
    return loss_sum / max(1, batch_count)


def save_checkpoint(path, model, config, step, loss, distributed, rank, plan, sessions_completed, eval_loss):
    target = Path(path)
    if distributed:
        from torch.distributed.fsdp import FullyShardedDataParallel as FSDP
        from torch.distributed.fsdp import FullStateDictConfig, StateDictType
        with FSDP.state_dict_type(
            model,
            StateDictType.FULL_STATE_DICT,
            FullStateDictConfig(offload_to_cpu=True, rank0_only=True),
        ):
            state = model.state_dict()
        if rank != 0:
            return
    else:
        state = {name: value.detach().cpu() for name, value in model.state_dict().items()}
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    weights = {}
    for name in list(state.keys()):
        value = state.pop(name)
        weights[name] = value.to(dtype=torch.bfloat16)
        del value
    torch.save({
        "model": weights,
        "config": config.to_dict(),
        "step": int(step),
        "loss": float(loss),
        "validation_loss": None if eval_loss is None else float(eval_loss),
        "parameter_count": estimate_parameters(config),
        "weight_dtype": "bfloat16",
        "training_from_scratch": True,
        "session_mesh": plan.as_dict(sessions_completed),
    }, temporary)
    temporary.replace(target)


def main():
    parser = argparse.ArgumentParser(description="Train KoworkLM from scratch using 100 logical session meshes.")
    parser.add_argument("--tokens", default="data/processed/train.bin")
    parser.add_argument("--validation-tokens", default="data/processed/valid.bin")
    parser.add_argument("--tokenizer", default="data/processed/kowork.model")
    parser.add_argument("--config", default="ai/config.json")
    parser.add_argument("--output", default="checkpoints/kowork-10b.pt")
    parser.add_argument("--steps", type=int, default=None)
    parser.add_argument("--max-sessions", type=int, default=None)
    parser.add_argument("--mesh-plan", default="ai/mesh_plan.json")
    parser.add_argument("--mesh-count", type=int, default=None)
    parser.add_argument("--sessions-per-mesh", type=int, default=None)
    parser.add_argument("--sequence-length", type=int, default=2048)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=0.0001)
    parser.add_argument("--min-learning-rate", type=float, default=0.00001)
    parser.add_argument("--warmup-steps", type=int, default=2000)
    parser.add_argument("--checkpoint-every", type=int, default=500)
    parser.add_argument("--eval-every", type=int, default=500)
    parser.add_argument("--eval-batches", type=int, default=8)
    parser.add_argument("--early-stopping-patience", type=int, default=0)
    parser.add_argument("--metrics-file", default=None)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--profile", choices=("10b", "smoke"), default="10b")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if args.steps is not None and args.steps < 1:
        parser.error("steps must be positive when provided")
    if min(args.batch_size, args.gradient_accumulation, args.checkpoint_every, args.eval_every, args.eval_batches) < 1:
        parser.error("Batch, accumulation, checkpoint and evaluation counts must be positive")
    mesh_config_path = Path(args.mesh_plan)
    if not mesh_config_path.is_file():
        parser.error("mesh-plan file does not exist: {}".format(mesh_config_path))
    mesh_config = json.loads(mesh_config_path.read_text(encoding="utf-8"))
    args.mesh_count = mesh_config["mesh_count"] if args.mesh_count is None else args.mesh_count
    args.sessions_per_mesh = mesh_config["sessions_per_mesh"] if args.sessions_per_mesh is None else args.sessions_per_mesh
    if args.mesh_count < 1 or args.sessions_per_mesh < 1:
        parser.error("mesh-count and sessions-per-mesh must be positive")
    if args.max_sessions is not None and args.max_sessions < 1:
        parser.error("max-sessions must be positive when provided")
    if args.early_stopping_patience < 0:
        parser.error("early-stopping-patience cannot be negative")
    if args.sequence_length < 2 or args.learning_rate <= 0 or args.min_learning_rate < 0:
        parser.error("Invalid sequence length or learning rate")
    if args.min_learning_rate > args.learning_rate:
        parser.error("Minimum learning rate cannot exceed initial learning rate")

    world_size, local_rank, rank = setup_distributed()
    distributed = world_size > 1
    if args.profile == "10b":
        config = ModelConfig.from_json(args.config)
        if not distributed:
            raise SystemExit("10B training needs a multi-process torchrun launch. Use --profile smoke for a local test.")
        if not torch.cuda.is_available():
            raise SystemExit("The 10B profile requires CUDA GPUs.")
        if not torch.cuda.is_bf16_supported():
            raise SystemExit("The 10B profile requires CUDA bfloat16 support.")
        if args.sequence_length > config.max_seq_len:
            parser.error("Sequence length exceeds the model configuration")
    else:
        config = None
        if args.steps is None:
            args.steps = 1000
        if args.batch_size * args.sequence_length > 65536:
            parser.error("Smoke profile batch times sequence length is too large")

    if args.device == "cuda" and not torch.cuda.is_available():
        raise SystemExit("CUDA was requested but is unavailable.")
    if args.device == "cpu":
        if args.profile == "10b":
            raise SystemExit("The 10B profile cannot be forced to CPU.")
        device = torch.device("cpu")
    elif torch.cuda.is_available():
        device = torch.device("cuda", local_rank) if distributed else torch.device("cuda")
        torch.cuda.set_device(device)
    else:
        device = torch.device("cpu")

    tokenizer_path = Path(args.tokenizer)
    if not tokenizer_path.is_file():
        raise SystemExit("Missing tokenizer: {}".format(tokenizer_path))
    import sentencepiece as spm
    processor = spm.SentencePieceProcessor(model_file=str(tokenizer_path))
    if config is None:
        config = tiny_config(vocab_size=processor.get_piece_size())
        args.sequence_length = min(args.sequence_length, config.max_seq_len)
    if processor.get_piece_size() != config.vocab_size:
        raise SystemExit("Tokenizer has {} pieces but model requires {}. Rebuild tokenizer with matching --vocab-size.".format(processor.get_piece_size(), config.vocab_size))

    tokens = load_tokens(args.tokens, config.vocab_size, args.sequence_length)
    validation_path = Path(args.validation_tokens)
    valid_tokens = load_tokens(validation_path, config.vocab_size, args.sequence_length, required=False) if validation_path.exists() else None
    plan = SessionMeshPlan(args.mesh_count, args.sessions_per_mesh)
    global_sessions_per_step = args.batch_size * args.gradient_accumulation * world_size
    target_sessions = plan.total_sessions
    if args.max_sessions is not None:
        target_sessions = min(target_sessions, args.max_sessions)
    if args.steps is not None:
        target_sessions = min(target_sessions, args.steps * global_sessions_per_step)
    if args.steps is None and args.max_sessions is None and target_sessions != plan.total_sessions:
        raise SystemExit("The full session budget was unexpectedly capped.")
    if target_sessions % global_sessions_per_step:
        if args.steps is None and args.max_sessions is None:
            raise SystemExit("The 40-billion-session plan is not divisible by the global batch. Adjust batch/accumulation or use --max-sessions for a bounded run.")
        target_sessions = target_sessions // global_sessions_per_step * global_sessions_per_step
    step_limit = target_sessions // global_sessions_per_step
    if step_limit < 1:
        raise SystemExit("The effective session budget is smaller than one distributed optimizer step.")

    torch.manual_seed(args.seed)
    model = create_model(config, device, distributed)
    torch.manual_seed(args.seed + 1000 + rank)
    np.random.seed(args.seed + rank)
    random.seed(args.seed + rank)
    parameter_count = sum(parameter.numel() for parameter in model.parameters()) if not distributed else estimate_parameters(config)
    metrics_path = Path(args.metrics_file) if args.metrics_file else Path(args.output).with_suffix(".metrics.jsonl")
    if rank == 0:
        print(json.dumps({
            "status": "initialized",
            "profile": args.profile,
            "device": str(device),
            "world_size": world_size,
            "parameters": parameter_count,
            "training_tokens": len(tokens),
            "validation_tokens": len(valid_tokens) if valid_tokens is not None else 0,
            "mesh_count": args.mesh_count,
            "sessions_per_mesh": args.sessions_per_mesh,
            "planned_sessions": plan.total_sessions,
            "effective_sessions_this_run": target_sessions,
            "mesh_plan_file": str(mesh_config_path),
            "mesh_plan_description": mesh_config.get("description", ""),
            "sessions_per_optimizer_step": global_sessions_per_step,
            "optimizer_steps_this_run": step_limit,
        }), flush=True)

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, betas=(0.9, 0.95), weight_decay=0.1, eps=1e-8)
    rngs = [np.random.default_rng(args.seed + rank * 1_000_003 + mesh_id) for mesh_id in range(args.mesh_count)]
    model.train()
    started = time.monotonic()
    current_loss = float("inf")
    validation_loss = None
    best_validation_loss = float("inf")
    patience_count = 0
    successful = False
    try:
        for step in range(1, step_limit + 1):
            if step <= args.warmup_steps:
                factor = step / max(1, args.warmup_steps)
            else:
                progress = (step - args.warmup_steps) / max(1, step_limit - args.warmup_steps)
                floor = args.min_learning_rate / args.learning_rate
                factor = max(floor, 0.5 * (1 + math.cos(math.pi * min(1.0, progress))))
            for group in optimizer.param_groups:
                group["lr"] = args.learning_rate * factor

            optimizer.zero_grad(set_to_none=True)
            total_loss = 0.0
            for micro_step in range(args.gradient_accumulation):
                session_ids = plan.session_ids(step - 1, micro_step, rank, args.batch_size, args.gradient_accumulation, world_size)
                mesh_ids = [session_id % args.mesh_count for session_id in session_ids]
                batch = sample_training_batch(tokens, args.sequence_length, mesh_ids, args.mesh_count, rngs, device)
                context = torch.autocast("cuda", dtype=torch.bfloat16) if device.type == "cuda" else nullcontext()
                with context:
                    logits = model(batch[:, :-1])
                    loss = F.cross_entropy(logits.float().reshape(-1, config.vocab_size), batch[:, 1:].reshape(-1))
                    scaled_loss = loss / args.gradient_accumulation
                if not torch.isfinite(loss):
                    raise SystemExit("Non-finite loss at training step {}".format(step))
                scaled_loss.backward()
                total_loss += float(loss.detach().cpu())

            if distributed:
                model.clip_grad_norm_(1.0)
            else:
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            current_loss = total_loss / args.gradient_accumulation
            sessions_completed = step * global_sessions_per_step
            should_evaluate = valid_tokens is not None and (step % args.eval_every == 0 or step == step_limit)
            should_checkpoint = step % args.checkpoint_every == 0 or step == step_limit or should_evaluate
            if should_evaluate:
                validation_loss = evaluate(
                    model, valid_tokens, config, args.sequence_length, args.batch_size,
                    args.eval_batches, device, rank, world_size, args.seed + step,
                )
                if validation_loss < best_validation_loss:
                    best_validation_loss = validation_loss
                    patience_count = 0
                else:
                    patience_count += 1
            if should_checkpoint:
                save_checkpoint(args.output, model, config, step, current_loss, distributed, rank, plan, sessions_completed, validation_loss)
                if rank == 0:
                    record = {
                        "step": step,
                        "training_loss": current_loss,
                        "validation_loss": validation_loss,
                        "elapsed_seconds": round(time.monotonic() - started, 2),
                        "sessions_completed": sessions_completed,
                        "session_target": plan.total_sessions,
                        "sessions_per_mesh_completed": plan.progress(sessions_completed),
                        "mesh_count": plan.mesh_count,
                        "sessions_per_mesh_target": plan.sessions_per_mesh,
                        "learning_rate": optimizer.param_groups[0]["lr"],
                        "checkpoint": str(args.output),
                    }
                    metrics_path.parent.mkdir(parents=True, exist_ok=True)
                    with metrics_path.open("a", encoding="utf-8") as sink:
                        sink.write(json.dumps(record) + "\n")
                    print(json.dumps({
                        "status": "training",
                        "step": step,
                        "loss": round(current_loss, 6),
                        "validation_loss": None if validation_loss is None else round(validation_loss, 6),
                        "sessions_completed": sessions_completed,
                        "elapsed_seconds": round(time.monotonic() - started, 2),
                        "checkpoint": args.output,
                        "metrics": str(metrics_path),
                    }), flush=True)
            if should_evaluate and args.early_stopping_patience > 0 and patience_count >= args.early_stopping_patience:
                if rank == 0:
                    print(json.dumps({"status": "early_stopping", "step": step, "best_validation_loss": best_validation_loss}), flush=True)
                break
        successful = True
    finally:
        if distributed and dist.is_initialized():
            if successful:
                dist.barrier()
            dist.destroy_process_group()

    if rank == 0:
        print(json.dumps({
            "status": "completed",
            "step": step,
            "final_loss": current_loss,
            "final_validation_loss": validation_loss,
            "parameters": parameter_count,
            "sessions_completed": min(step * global_sessions_per_step, plan.total_sessions),
            "session_target": plan.total_sessions,
            "sessions_per_mesh_completed": plan.progress(min(step * global_sessions_per_step, plan.total_sessions)),
            "elapsed_seconds": round(time.monotonic() - started, 2),
            "checkpoint": args.output,
            "metrics": str(metrics_path),
        }), flush=True)


if __name__ == "__main__":
    main()
