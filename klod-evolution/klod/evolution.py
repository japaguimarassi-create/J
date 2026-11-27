import argparse
import json
import multiprocessing as mp
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import torch

from .model import KlodModel, ModelConfig


@dataclass
class Candidate:
    name: str
    d_model: int
    n_heads: int
    n_layers: int
    n_experts: int

    def model_config(self) -> ModelConfig:
        return ModelConfig(
            vocab_size=258,
            d_model=self.d_model,
            n_heads=self.n_heads,
            n_layers=self.n_layers,
            n_experts=self.n_experts,
            max_seq_len=64,
            dropout=0.0,
        )


def _worker(send_pipe, candidate_data: dict) -> None:
    try:
        torch.set_num_threads(1)
        candidate = Candidate(**candidate_data)
        torch.manual_seed(1234)
        started = time.perf_counter()
        model = KlodModel(candidate.model_config()).eval()
        sample = torch.randint(2, 258, (1, 16), dtype=torch.long)
        with torch.inference_mode():
            logits, _ = model(sample)
        checks = {
            "constructs": True,
            "shape_ok": list(logits.shape) == [1, 16, 258],
            "finite_logits": bool(torch.isfinite(logits).all()),
            "parameter_count_positive": sum(p.numel() for p in model.parameters()) > 0,
        }
        send_pipe.send({
            "candidate": candidate.name,
            "checks": checks,
            "passed": all(checks.values()),
            "score": sum(checks.values()) / len(checks),
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
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


def evaluate(candidate: Candidate, timeout_seconds: float = 20.0) -> dict:
    context = mp.get_context("spawn")
    receive_pipe, send_pipe = context.Pipe(duplex=False)
    process = context.Process(target=_worker, args=(send_pipe, asdict(candidate)), daemon=True)
    process.start()
    send_pipe.close()
    try:
        if receive_pipe.poll(timeout_seconds):
            result = receive_pipe.recv()
        else:
            result = {"candidate": candidate.name, "passed": False, "error": "worker timeout"}
            process.terminate()
        process.join(timeout=2)
        if process.is_alive():
            process.kill()
            process.join(timeout=2)
            result["forced_worker_shutdown"] = True
        result["worker_exit_code"] = process.exitcode
        return result
    finally:
        receive_pipe.close()
        if process.is_alive():
            process.terminate()
            process.join(timeout=2)


def build_candidates(rounds: int) -> list[Candidate]:
    templates = [
        (64, 4, 2, 2),
        (96, 4, 2, 4),
        (128, 4, 3, 2),
        (128, 8, 2, 4),
        (192, 6, 3, 4),
        (256, 8, 4, 4),
    ]
    return [Candidate(f"candidate-{index + 1}", *templates[index % len(templates)]) for index in range(rounds)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run bounded, isolated KLOD candidate selection")
    parser.add_argument("--rounds", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--promote", action="store_true", help="write the selected runtime config; requires this explicit flag")
    parser.add_argument("--out", type=Path, default=Path("runs/evolution-report.json"))
    args = parser.parse_args()
    if not 1 <= args.rounds <= 20:
        raise SystemExit("--rounds must be between 1 and 20")
    if not 1 <= args.timeout <= 120:
        raise SystemExit("--timeout must be between 1 and 120 seconds")

    candidates = build_candidates(args.rounds)
    results = [evaluate(candidate, args.timeout) for candidate in candidates]
    passing = [item for item in results if item.get("passed")]
    selected = min(passing, key=lambda item: item.get("latency_ms", float("inf")), default=None)
    report = {
        "results": results,
        "selected_candidate": selected.get("candidate") if selected else None,
        "selection_scope": "integrity and inference smoke tests only; not language quality",
        "promoted": False,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if selected and args.promote:
        selected_spec = next(c for c in candidates if c.name == selected["candidate"])
        promotion = {
            "candidate": asdict(selected_spec),
            "requires_training": True,
            "human_requested_promotion": True,
            "quality_claim": "not established; only smoke tests passed",
        }
        Path("runs/selected-runtime.json").write_text(json.dumps(promotion, indent=2), encoding="utf-8")
        report["promoted"] = True
        args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))
    if not passing:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
