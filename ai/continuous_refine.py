import argparse
import json
import math
import random
import time
from collections import deque
from pathlib import Path

import numpy as np
import torch
from torch.nn import functional as F

from ai.config import estimate_parameters, tiny_config
from ai.model import KoworkLM


def read_tokens(path, vocab_size, seq_len):
    source = Path(path)
    if not source.is_file():
        raise SystemExit("Token file not found: {}".format(source))
    if source.stat().st_size % 2:
        raise SystemExit("Token file has an invalid uint16 size: {}".format(source))
    values = np.memmap(source, dtype="<u2", mode="r")
    if len(values) <= seq_len + 1:
        raise SystemExit("Token file is too short: {}".format(source))
    if int(values.max()) >= vocab_size:
        raise SystemExit("Token ID exceeds tokenizer vocabulary: {}".format(source))
    return values


def make_window(tokens, start, seq_len):
    return torch.as_tensor(np.array(tokens[start:start + seq_len + 1], dtype=np.int64)[None, :])


def evaluate(model, batches):
    model.eval()
    losses = []
    with torch.inference_mode():
        for batch in batches:
            logits = model(batch[:, :-1])
            loss = F.cross_entropy(logits.float().reshape(-1, model.config.vocab_size), batch[:, 1:].reshape(-1))
            losses.append(float(loss.item()))
    model.train()
    return sum(losses) / len(losses)


def save_state(path, model, optimizer, config, global_step, target_cycles, best_rolling, best_cycle, rng):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    torch.save({
        "model": model.state_dict(),
        "optimizer": optimizer.state_dict(),
        "config": config.to_dict(),
        "global_step": int(global_step),
        "step": int(global_step),
        "target_cycles": int(target_cycles),
        "best_rolling_validation_loss": float(best_rolling),
        "best_cycle": int(best_cycle),
        "numpy_rng_state": rng.bit_generator.state,
        "torch_rng_state": torch.get_rng_state(),
        "python_rng_state": random.getstate(),
        "parameter_count": estimate_parameters(config),
        "training_profile": "continuous_tiny_cpu_refinement",
        "checkpoint_kind": "resumable_training_state",
    }, temporary)
    temporary.replace(target)


def save_best(path, model, config, global_step, validation_loss, rolling_loss):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    torch.save({
        "model": {name: value.detach().cpu().clone() for name, value in model.state_dict().items()},
        "config": config.to_dict(),
        "step": int(global_step),
        "global_step": int(global_step),
        "validation_loss": float(validation_loss),
        "rolling_validation_loss": float(rolling_loss),
        "parameter_count": estimate_parameters(config),
        "training_profile": "continuous_tiny_cpu_refinement",
        "checkpoint_kind": "best_rolling_validation_model_only",
        "training_from_scratch": False,
    }, temporary)
    temporary.replace(target)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--total-cycles", type=int, default=16_820_000)
    parser.add_argument("--max-updates-this-run", type=int, default=1000)
    parser.add_argument("--train-tokens", default="data/smoke/train.bin")
    parser.add_argument("--valid-tokens", default="data/smoke/valid.bin")
    parser.add_argument("--tokenizer", default="data/smoke/kowork.model")
    parser.add_argument("--init-checkpoint", default="checkpoints/mesh-smoke-final.pt")
    parser.add_argument("--resume", default="")
    parser.add_argument("--output-dir", default="checkpoints/continuous-16820x1000")
    parser.add_argument("--sequence-length", type=int, default=64)
    parser.add_argument("--learning-rate", type=float, default=None)
    parser.add_argument("--min-learning-rate", type=float, default=None)
    parser.add_argument("--checkpoint-every", type=int, default=1000)
    parser.add_argument("--eval-every", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=16820)
    args = parser.parse_args()

    if args.total_cycles < 1 or args.max_updates_this_run < 1:
        parser.error("total-cycles and max-updates-this-run must be positive")
    if args.sequence_length < 2 or args.sequence_length > 128:
        parser.error("sequence-length must be between 2 and 128")
    requested_learning_rate = args.learning_rate
    requested_min_learning_rate = args.min_learning_rate
    if args.learning_rate is None:
        args.learning_rate = 0.00003
    if args.min_learning_rate is None:
        args.min_learning_rate = min(0.000001, args.learning_rate)
    if args.learning_rate <= 0 or args.min_learning_rate <= 0 or args.min_learning_rate > args.learning_rate:
        parser.error("learning rates must be positive and min-learning-rate cannot exceed learning-rate")
    if args.checkpoint_every < 1 or args.eval_every < 1:
        parser.error("checkpoint-every and eval-every must be positive")

    torch.set_num_threads(min(3, torch.get_num_threads()))
    torch.manual_seed(args.seed)
    random.seed(args.seed)
    rng = np.random.default_rng(args.seed)

    import sentencepiece as spm
    tokenizer = spm.SentencePieceProcessor(model_file=args.tokenizer)
    config = tiny_config(vocab_size=tokenizer.get_piece_size())
    train_tokens = read_tokens(args.train_tokens, config.vocab_size, args.sequence_length)
    valid_tokens = read_tokens(args.valid_tokens, config.vocab_size, args.sequence_length)
    max_train_start = len(train_tokens) - args.sequence_length - 1
    max_valid_start = len(valid_tokens) - args.sequence_length - 1
    valid_starts = np.linspace(0, max_valid_start, num=4, dtype=np.int64).tolist()
    valid_batches = [make_window(valid_tokens, int(start), args.sequence_length) for start in valid_starts]
    train_buckets = np.linspace(0, max_train_start, num=100, dtype=np.int64).tolist()

    model = KoworkLM(config).cpu()
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, betas=(0.9, 0.95), weight_decay=0.01)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    history_path = output_dir / "comparisons.jsonl"
    latest_path = output_dir / "latest.pt"
    best_path = output_dir / "best.pt"
    resume_optimizer = False
    global_step = 0
    best_rolling = float("inf")
    best_cycle = 0
    rolling = deque(maxlen=10)

    if args.resume:
        resume_path = Path(args.resume)
        if not resume_path.is_file():
            raise SystemExit("Resume checkpoint not found: {}".format(resume_path))
        payload = torch.load(resume_path, map_location="cpu", weights_only=False)
        if payload.get("config") != config.to_dict() or payload.get("parameter_count") != estimate_parameters(config):
            raise SystemExit("Resume checkpoint architecture does not match this run.")
        model.load_state_dict(payload["model"], strict=True)
        global_step = int(payload.get("global_step", payload.get("step", 0)))
        if global_step >= args.total_cycles:
            raise SystemExit("Checkpoint already reached or exceeded total-cycles.")
        if "optimizer" in payload:
            optimizer.load_state_dict(payload["optimizer"])
            resume_optimizer = True
            if requested_learning_rate is None:
                args.learning_rate = float(optimizer.param_groups[0]["lr"])
            if requested_min_learning_rate is None:
                args.min_learning_rate = min(0.000001, args.learning_rate)
            if args.min_learning_rate > args.learning_rate:
                raise SystemExit("Saved learning rate is below the requested minimum learning rate.")
        if "numpy_rng_state" in payload:
            rng.bit_generator.state = payload["numpy_rng_state"]
        if "torch_rng_state" in payload:
            torch.set_rng_state(payload["torch_rng_state"])
        if "python_rng_state" in payload:
            random.setstate(payload["python_rng_state"])
        best_rolling = float(payload.get("best_rolling_validation_loss", float("inf")))
        best_cycle = int(payload.get("best_cycle", 0))
        if history_path.is_file():
            for line in history_path.read_text(encoding="utf-8").splitlines()[-10:]:
                try:
                    item = json.loads(line)
                    if "validation_loss" in item:
                        rolling.append(float(item["validation_loss"]))
                except (ValueError, TypeError):
                    continue
    else:
        init_path = Path(args.init_checkpoint)
        if not init_path.is_file():
            raise SystemExit("Initial checkpoint not found: {}".format(init_path))
        payload = torch.load(init_path, map_location="cpu", weights_only=False)
        if payload.get("config") != config.to_dict() or payload.get("parameter_count") != estimate_parameters(config):
            raise SystemExit("Initial checkpoint architecture does not match this run.")
        model.load_state_dict(payload["model"], strict=True)
        global_step = int(payload.get("global_step", payload.get("step", 0)))
        if global_step >= args.total_cycles:
            raise SystemExit("Initial checkpoint step already reached or exceeded total-cycles.")
        if history_path.exists():
            history_path.unlink()

    baseline_loss = evaluate(model, valid_batches)
    if not args.resume:
        best_rolling = baseline_loss
        best_cycle = global_step
        save_best(best_path, model, config, global_step, baseline_loss, baseline_loss)
    remaining = args.total_cycles - global_step
    updates_to_run = min(remaining, args.max_updates_this_run)
    start_time = time.monotonic()
    training_losses = deque(maxlen=100)
    last_validation = baseline_loss
    update_end = global_step + updates_to_run

    with history_path.open("a", encoding="utf-8") as history:
        for step in range(global_step + 1, update_end + 1):
            progress = (step - 1) / max(1, args.total_cycles - 1)
            lr = args.min_learning_rate + (args.learning_rate - args.min_learning_rate) * 0.5 * (1 + math.cos(math.pi * progress))
            for group in optimizer.param_groups:
                group["lr"] = lr
            base_start = int(rng.choice(train_buckets))
            start = int(np.clip(base_start + int(rng.integers(-128, 129)), 0, max_train_start))
            batch = make_window(train_tokens, start, args.sequence_length)
            model.train()
            optimizer.zero_grad(set_to_none=True)
            logits = model(batch[:, :-1])
            loss = F.cross_entropy(logits.float().reshape(-1, config.vocab_size), batch[:, 1:].reshape(-1))
            if not torch.isfinite(loss):
                raise SystemExit("Non-finite training loss at global cycle {}".format(step))
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            training_losses.append(float(loss.item()))

            if step % args.eval_every == 0 or step == update_end or step == args.total_cycles:
                last_validation = evaluate(model, valid_batches)
                rolling.append(last_validation)
                rolling_loss = sum(rolling) / len(rolling)
                improved = len(rolling) == rolling.maxlen and rolling_loss < best_rolling
                if improved:
                    best_rolling = rolling_loss
                    best_cycle = step
                    save_best(best_path, model, config, step, last_validation, rolling_loss)
                row = {
                    "global_cycle": step,
                    "target_cycles": args.total_cycles,
                    "training_loss_mean_since_previous_eval": sum(training_losses) / max(1, len(training_losses)),
                    "validation_loss": last_validation,
                    "rolling_validation_loss_10_evaluations": rolling_loss,
                    "best_rolling_validation_loss": best_rolling if math.isfinite(best_rolling) else None,
                    "best_cycle": best_cycle,
                    "improved_rolling_validation": improved,
                    "learning_rate": lr,
                    "source_checkpoint_step": global_step if not args.resume else None,
                }
                history.write(json.dumps(row, separators=(",", ":")) + "\n")
                history.flush()
                print(json.dumps({
                    "status": "running",
                    "global_cycle": step,
                    "target_cycles": args.total_cycles,
                    "updates_this_run": step - global_step,
                    "training_loss_mean_since_previous_eval": round(row["training_loss_mean_since_previous_eval"], 5),
                    "validation_loss": round(last_validation, 5),
                    "rolling_validation_loss_10_evaluations": round(rolling_loss, 5),
                    "best_cycle": best_cycle,
                    "elapsed_seconds": round(time.monotonic() - start_time, 1),
                }), flush=True)
                training_losses.clear()

            if step % args.checkpoint_every == 0 or step == update_end or step == args.total_cycles:
                save_state(latest_path, model, optimizer, config, step, args.total_cycles, best_rolling, best_cycle, rng)

    complete = update_end >= args.total_cycles
    report = {
        "target_cycles": args.total_cycles,
        "starting_global_cycle": global_step,
        "completed_global_cycle": update_end,
        "updates_completed_this_run": updates_to_run,
        "complete_target_reached": complete,
        "model_parameters": estimate_parameters(config),
        "model_profile": "623k-parameter CPU comparison model, not the 10B model",
        "initialized_from": args.resume or args.init_checkpoint,
        "optimizer_state_resumed": resume_optimizer,
        "training_tokens": int(len(train_tokens)),
        "validation_tokens": int(len(valid_tokens)),
        "tokenizer_vocab_size": tokenizer.get_piece_size(),
        "sequence_length": args.sequence_length,
        "learning_rate_base_for_this_run": args.learning_rate,
        "learning_rate_minimum_for_this_run": args.min_learning_rate,
        "baseline_validation_loss_at_run_start": baseline_loss,
        "last_validation_loss": last_validation,
        "best_rolling_validation_loss": best_rolling,
        "best_cycle": best_cycle,
        "elapsed_seconds": round(time.monotonic() - start_time, 2),
        "history_file": str(history_path),
        "latest_resumable_checkpoint": str(latest_path),
        "best_model_checkpoint": str(best_path),
        "limitations": [
            "This is a tiny comparison model, not the configured 10B-parameter model.",
            "The available corpus is small and does not establish broad reasoning ability.",
            "Long repetition on the same corpus can overfit; held-out loss is recorded for comparison.",
            "The exact weights from the interrupted 16820-cycle run were unavailable because that run had no periodic resumable checkpoint.",
        ],
    }
    (output_dir / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "completed" if complete else "paused_with_checkpoint", **report}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
