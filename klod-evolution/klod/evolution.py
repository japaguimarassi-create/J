import argparse
import json
import multiprocessing as mp
import shutil
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import torch

from .model import ByteTokenizer, KlodModel, ModelConfig
from .train import read_corpus


@dataclass
class Candidate:
    name: str
    d_model: int
    n_heads: int
    n_layers: int
    n_experts: int

    def model_config(self, seq_len: int) -> ModelConfig:
        return ModelConfig(
            vocab_size=ByteTokenizer.vocab_size,
            d_model=self.d_model,
            n_heads=self.n_heads,
            n_layers=self.n_layers,
            n_experts=self.n_experts,
            max_seq_len=seq_len,
            dropout=0.05,
        )


def _sample_batch(data: torch.Tensor, batch_size: int, seq_len: int) -> tuple[torch.Tensor, torch.Tensor]:
    upper = data.numel() - seq_len - 1
    if upper < 1:
        raise ValueError("Corpus split is too small for the selected sequence length")
    starts = torch.randint(0, upper, (batch_size,))
    inputs = torch.stack([data[start:start + seq_len] for start in starts])
    targets = torch.stack([data[start + 1:start + seq_len + 1] for start in starts])
    return inputs, targets


def _mean_loss(model: KlodModel, data: torch.Tensor, seq_len: int, max_windows: int = 32) -> float:
    upper = data.numel() - seq_len - 1
    if upper < 1:
        raise ValueError("Validation split is too small")
    count = min(max_windows, upper)
    starts = torch.linspace(0, upper - 1, steps=count).long().unique().tolist()
    losses = []
    model.eval()
    with torch.inference_mode():
        for start in starts:
            inputs = data[start:start + seq_len].unsqueeze(0)
            targets = data[start + 1:start + seq_len + 1].unsqueeze(0)
            _, loss = model(inputs, targets)
            if loss is None or not torch.isfinite(loss):
                raise RuntimeError("Non-finite evaluation loss")
            losses.append(float(loss.cpu()))
    model.train()
    return sum(losses) / len(losses)


def _candidate_worker(
    send_pipe,
    candidate_data: dict,
    corpus_path: str,
    steps: int,
    batch_size: int,
    seq_len: int,
    checkpoint_dir: str,
) -> None:
    try:
        torch.set_num_threads(1)
        torch.manual_seed(1701)
        candidate = Candidate(**candidate_data)
        corpus = read_corpus(Path(corpus_path))
        token_ids = ByteTokenizer().encode(corpus)
        split = int(len(token_ids) * 0.82)
        training_data = torch.tensor(token_ids[:split], dtype=torch.long)
        validation_data = torch.tensor(token_ids[split:], dtype=torch.long)
        if training_data.numel() <= seq_len + 1 or validation_data.numel() <= seq_len + 1:
            raise ValueError(
                f"Need more corpus data for seq_len={seq_len}; "
                f"train_tokens={training_data.numel()}, validation_tokens={validation_data.numel()}"
            )

        model = KlodModel(candidate.model_config(seq_len))
        optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4)
        initial_train_loss = _mean_loss(model, training_data, seq_len)
        started = time.perf_counter()

        for _ in range(steps):
            inputs, targets = _sample_batch(training_data, batch_size, seq_len)
            optimizer.zero_grad(set_to_none=True)
            _, loss = model(inputs, targets)
            if loss is None or not torch.isfinite(loss):
                raise RuntimeError("Training produced a non-finite loss")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()

        final_train_loss = _mean_loss(model, training_data, seq_len)
        validation_loss = _mean_loss(model, validation_data, seq_len)
        elapsed = time.perf_counter() - started
        parameter_count = sum(parameter.numel() for parameter in model.parameters())
        checkpoint_path = Path(checkpoint_dir) / f"{candidate.name}.pt"
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        torch.save({
            "config": model.export_config(),
            "state_dict": model.state_dict(),
            "training": {
                "steps": steps,
                "final_train_loss": final_train_loss,
                "validation_loss": validation_loss,
                "candidate": candidate.name,
                "corpus_tokens": len(token_ids),
            },
        }, checkpoint_path)

        checks = {
            "finite_train_loss": torch.isfinite(torch.tensor(final_train_loss)).item(),
            "finite_validation_loss": torch.isfinite(torch.tensor(validation_loss)).item(),
            "checkpoint_written": checkpoint_path.is_file() and checkpoint_path.stat().st_size > 0,
            "parameter_count_positive": parameter_count > 0,
        }
        send_pipe.send({
            "candidate": candidate.name,
            "config": asdict(candidate),
            "checks": checks,
            "passed": all(checks.values()),
            "initial_train_loss": initial_train_loss,
            "final_train_loss": final_train_loss,
            "validation_loss": validation_loss,
            "training_improved": final_train_loss < initial_train_loss,
            "parameter_count": parameter_count,
            "training_seconds": round(elapsed, 3),
            "checkpoint": str(checkpoint_path),
        })
    except BaseException as exc:
        try:
            send_pipe.send({
                "candidate": candidate_data.get("name", "unknown"),
                "passed": False,
                "error": f"{type(exc).__name__}: {exc}",
            })
        except Exception:
            pass
    finally:
        send_pipe.close()


def evaluate(
    candidate: Candidate,
    corpus_path: str,
    steps: int = 80,
    batch_size: int = 4,
    seq_len: int = 24,
    timeout_seconds: float = 120,
    checkpoint_dir: str = "runs/evolution-candidates",
) -> dict:
    context = mp.get_context("spawn")
    receive_pipe, send_pipe = context.Pipe(duplex=False)
    process = context.Process(
        target=_candidate_worker,
        args=(send_pipe, asdict(candidate), corpus_path, steps, batch_size, seq_len, checkpoint_dir),
        daemon=True,
    )
    process.start()
    send_pipe.close()
    try:
        if receive_pipe.poll(timeout_seconds):
            result = receive_pipe.recv()
        else:
            result = {
                "candidate": candidate.name,
                "passed": False,
                "error": f"worker timeout after {timeout_seconds} seconds",
            }
            process.terminate()
        process.join(timeout=3)
        if process.is_alive():
            process.kill()
            process.join(timeout=3)
            result["worker_shutdown_for_timeout"] = True
        result["worker_exit_code"] = process.exitcode
        return result
    finally:
        receive_pipe.close()
        if process.is_alive():
            process.terminate()
            process.join(timeout=3)


def build_candidates(rounds: int) -> list[Candidate]:
    templates = [
        (32, 2, 1, 2),
        (48, 4, 2, 2),
        (64, 4, 2, 4),
        (64, 2, 3, 2),
        (96, 4, 2, 4),
        (96, 4, 3, 2),
        (128, 4, 2, 2),
        (128, 8, 2, 4),
    ]
    return [
        Candidate(f"candidate-{index + 1}", *templates[index % len(templates)])
        for index in range(rounds)
    ]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train and compare isolated KLOD candidates on held-out corpus data"
    )
    parser.add_argument("--rounds", type=int, default=4)
    parser.add_argument("--steps", type=int, default=80)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--seq-len", type=int, default=24)
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--checkpoint-dir", type=Path, default=Path("runs/evolution-candidates"))
    parser.add_argument("--out", type=Path, default=Path("runs/evolution-report.json"))
    parser.add_argument("--promote", action="store_true")
    parser.add_argument("--promoted-checkpoint", type=Path, default=Path("runs/klod-evolved.pt"))
    parser.add_argument("--overwrite-checkpoint", action="store_true")
    args = parser.parse_args()

    if not 1 <= args.rounds <= 20:
        raise SystemExit("--rounds must be between 1 and 20")
    if not 1 <= args.steps <= 100000:
        raise SystemExit("--steps must be between 1 and 100000")
    if not 1 <= args.batch_size <= 128:
        raise SystemExit("--batch-size must be between 1 and 128")
    if not 8 <= args.seq_len <= 8192:
        raise SystemExit("--seq-len must be between 8 and 8192")
    if not 10 <= args.timeout <= 600:
        raise SystemExit("--timeout must be between 10 and 600 seconds")
    if not args.data.is_file():
        raise SystemExit(f"Training corpus not found: {args.data}")
    if args.promote and args.promoted_checkpoint.exists() and not args.overwrite_checkpoint:
        raise SystemExit(
            f"Checkpoint already exists: {args.promoted_checkpoint}. "
            "Choose another path or pass --overwrite-checkpoint explicitly."
        )

    corpus = read_corpus(args.data)
    if len(ByteTokenizer().encode(corpus)) < args.seq_len * 2 + 10:
        raise SystemExit("Corpus is too small for a train/validation split at this sequence length")

    args.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    candidates = build_candidates(args.rounds)
    results = [
        evaluate(
            candidate,
            str(args.data.resolve()),
            args.steps,
            args.batch_size,
            args.seq_len,
            args.timeout,
            str(args.checkpoint_dir.resolve()),
        )
        for candidate in candidates
    ]
    passing = [item for item in results if item.get("passed")]
    selected = min(
        passing,
        key=lambda item: (item["validation_loss"], item["parameter_count"]),
        default=None,
    )

    report = {
        "results": results,
        "selected_candidate": selected.get("candidate") if selected else None,
        "selection_metric": "lowest held-out next-token cross-entropy, then fewer parameters",
        "corpus": str(args.data),
        "training_steps_per_candidate": args.steps,
        "automatic_promotion": False,
        "promoted": False,
        "limits": "Language quality and programming ability require separate reference benchmarks and human review.",
    }

    if selected and args.promote:
        args.promoted_checkpoint.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(selected["checkpoint"], args.promoted_checkpoint)
        report["promoted"] = True
        report["promoted_checkpoint"] = str(args.promoted_checkpoint)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not passing:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
