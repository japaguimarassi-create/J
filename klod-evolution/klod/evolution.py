import argparse
import json
import multiprocessing as mp
import random
import shutil
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

import torch

from .benchmarks import load_cases, normalize, token_f1
from .model import ByteTokenizer, KlodModel, ModelConfig
from .train import read_corpus


@dataclass
class Candidate:
    name: str
    d_model: int
    n_heads: int
    n_layers: int
    n_experts: int
    learning_rate: float = 0.0003
    dropout: float = 0.05
    generation: int = 1
    parent: str | None = None

    def model_config(self, seq_len: int) -> ModelConfig:
        return ModelConfig(
            vocab_size=ByteTokenizer.vocab_size,
            d_model=self.d_model,
            n_heads=self.n_heads,
            n_layers=self.n_layers,
            n_experts=self.n_experts,
            max_seq_len=seq_len,
            dropout=self.dropout,
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
    was_training = model.training
    model.eval()
    try:
        with torch.inference_mode():
            for start in starts:
                inputs = data[start:start + seq_len].unsqueeze(0)
                targets = data[start + 1:start + seq_len + 1].unsqueeze(0)
                _, loss = model(inputs, targets)
                if loss is None or not torch.isfinite(loss):
                    raise RuntimeError("Non-finite evaluation loss")
                losses.append(float(loss.detach().cpu()))
    finally:
        model.train(was_training)
    return sum(losses) / len(losses)


def _evaluate_tasks(
    model: KlodModel,
    tokenizer: ByteTokenizer,
    benchmark_path: str,
    max_new_tokens: int,
) -> dict:
    cases = load_cases(Path(benchmark_path))
    torch.manual_seed(2024)
    results = []
    category_scores = defaultdict(list)

    model.eval()
    for case in cases:
        prompt = f"\nUsuário: {case['prompt']}\nKLOD:"
        input_ids = torch.tensor(
            [tokenizer.encode(prompt, add_eos=False)],
            dtype=torch.long,
        )
        generated = model.generate(input_ids, max_new_tokens=max_new_tokens)
        prediction = tokenizer.decode(generated[0, input_ids.size(1):].tolist()).strip()
        expected = case["expected"]
        score = token_f1(prediction, expected)
        exact = normalize(prediction) == normalize(expected)
        results.append({
            "id": case["id"],
            "category": case["category"],
            "token_f1": score,
            "exact_match": exact,
        })
        category_scores[case["category"]].append(score)

    mean_f1 = sum(item["token_f1"] for item in results) / len(results)
    exact_rate = sum(item["exact_match"] for item in results) / len(results)
    return {
        "cases": len(results),
        "mean_token_f1": mean_f1,
        "exact_match_rate": exact_rate,
        "task_score": 0.75 * mean_f1 + 0.25 * exact_rate,
        "category_token_f1": {
            category: sum(scores) / len(scores)
            for category, scores in sorted(category_scores.items())
        },
        "details": results,
    }


def _candidate_worker(
    send_pipe,
    candidate_data: dict,
    corpus_path: str,
    benchmark_path: str,
    steps: int,
    batch_size: int,
    seq_len: int,
    benchmark_tokens: int,
    checkpoint_dir: str,
) -> None:
    try:
        torch.set_num_threads(1)
        torch.manual_seed(1701)
        candidate = Candidate(**candidate_data)
        tokenizer = ByteTokenizer()
        corpus = read_corpus(Path(corpus_path))
        token_ids = tokenizer.encode(corpus)
        split = int(len(token_ids) * 0.82)
        training_data = torch.tensor(token_ids[:split], dtype=torch.long)
        validation_data = torch.tensor(token_ids[split:], dtype=torch.long)
        if training_data.numel() <= seq_len + 1 or validation_data.numel() <= seq_len + 1:
            raise ValueError(
                f"Need more corpus data for seq_len={seq_len}; "
                f"train_tokens={training_data.numel()}, validation_tokens={validation_data.numel()}"
            )

        model = KlodModel(candidate.model_config(seq_len)).cpu()
        optimizer = torch.optim.AdamW(model.parameters(), lr=candidate.learning_rate)
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
        task_metrics = _evaluate_tasks(model, tokenizer, benchmark_path, benchmark_tokens)
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
                "task_score": task_metrics["task_score"],
                "candidate": candidate.name,
                "generation": candidate.generation,
                "parent": candidate.parent,
                "corpus_tokens": len(token_ids),
            },
        }, checkpoint_path)

        checks = {
            "finite_train_loss": torch.isfinite(torch.tensor(final_train_loss)).item(),
            "finite_validation_loss": torch.isfinite(torch.tensor(validation_loss)).item(),
            "finite_task_score": torch.isfinite(torch.tensor(task_metrics["task_score"])).item(),
            "benchmark_has_cases": task_metrics["cases"] > 0,
            "checkpoint_written": checkpoint_path.is_file() and checkpoint_path.stat().st_size > 0,
            "parameter_count_positive": parameter_count > 0,
        }
        send_pipe.send({
            "candidate": candidate.name,
            "generation": candidate.generation,
            "parent": candidate.parent,
            "config": asdict(candidate),
            "checks": checks,
            "passed": all(checks.values()),
            "initial_train_loss": initial_train_loss,
            "final_train_loss": final_train_loss,
            "training_improved": final_train_loss < initial_train_loss,
            "validation_loss": validation_loss,
            "benchmark": task_metrics,
            "task_score": task_metrics["task_score"],
            "parameter_count": parameter_count,
            "training_seconds": round(elapsed, 3),
            "checkpoint": str(checkpoint_path),
        })
    except BaseException as exc:
        try:
            send_pipe.send({
                "candidate": candidate_data.get("name", "unknown"),
                "generation": candidate_data.get("generation", 0),
                "parent": candidate_data.get("parent"),
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
    benchmark_path: str,
    steps: int = 80,
    batch_size: int = 4,
    seq_len: int = 24,
    benchmark_tokens: int = 64,
    timeout_seconds: float = 120,
    checkpoint_dir: str = "runs/evolution-candidates",
) -> dict:
    context = mp.get_context("spawn")
    receive_pipe, send_pipe = context.Pipe(duplex=False)
    process = context.Process(
        target=_candidate_worker,
        args=(
            send_pipe,
            asdict(candidate),
            corpus_path,
            benchmark_path,
            steps,
            batch_size,
            seq_len,
            benchmark_tokens,
            checkpoint_dir,
        ),
        daemon=True,
    )
    process.start()
    send_pipe.close()
    try:
        if receive_pipe.poll(timeout_seconds):
            try:
                result = receive_pipe.recv()
            except EOFError:
                result = {
                    "candidate": candidate.name,
                    "generation": candidate.generation,
                    "parent": candidate.parent,
                    "passed": False,
                    "error": "worker exited without a result",
                }
        else:
            result = {
                "candidate": candidate.name,
                "generation": candidate.generation,
                "parent": candidate.parent,
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


def build_candidates(population_size: int, seed: int = 42) -> list[Candidate]:
    templates = [
        (32, 2, 1, 2),
        (48, 4, 2, 2),
        (64, 4, 2, 4),
        (64, 2, 3, 2),
        (96, 4, 2, 4),
        (96, 8, 3, 2),
        (128, 4, 2, 2),
        (128, 8, 2, 4),
    ]
    rng = random.Random(seed)
    selected = [templates[index % len(templates)] for index in range(population_size)]
    rng.shuffle(selected)
    return [
        Candidate(
            name=f"g1-candidate-{index + 1}",
            d_model=values[0],
            n_heads=values[1],
            n_layers=values[2],
            n_experts=values[3],
            generation=1,
        )
        for index, values in enumerate(selected)
    ]


def mutate_candidate(parent: Candidate, name: str, generation: int, rng: random.Random) -> Candidate:
    widths = [32, 48, 64, 96, 128, 160]
    head_options = [2, 4, 8]
    layer_options = [1, 2, 3, 4, 5]
    expert_options = [2, 4, 6, 8]
    learning_rates = [0.0001, 0.0002, 0.0003, 0.0005, 0.0008]
    dropout_options = [0.0, 0.05, 0.1, 0.15, 0.2]

    for _ in range(32):
        width = rng.choice(widths) if rng.random() < 0.7 else parent.d_model
        valid_heads = [heads for heads in head_options if width % heads == 0]
        heads = rng.choice(valid_heads) if rng.random() < 0.65 else parent.n_heads
        if heads not in valid_heads:
            heads = rng.choice(valid_heads)
        layers = rng.choice(layer_options) if rng.random() < 0.65 else parent.n_layers
        experts = rng.choice(expert_options) if rng.random() < 0.65 else parent.n_experts
        learning_rate = rng.choice(learning_rates) if rng.random() < 0.55 else parent.learning_rate
        dropout = rng.choice(dropout_options) if rng.random() < 0.55 else parent.dropout
        genes = (width, heads, layers, experts, learning_rate, dropout)
        parent_genes = (
            parent.d_model,
            parent.n_heads,
            parent.n_layers,
            parent.n_experts,
            parent.learning_rate,
            parent.dropout,
        )
        if genes != parent_genes:
            return Candidate(
                name=name,
                d_model=width,
                n_heads=heads,
                n_layers=layers,
                n_experts=experts,
                learning_rate=learning_rate,
                dropout=dropout,
                generation=generation,
                parent=parent.name,
            )

    raise RuntimeError("Mutation did not produce a distinct architecture")


def rank_candidates(results: list[dict]) -> list[dict]:
    passing = [
        result for result in results
        if result.get("passed") and "task_score" in result and "validation_loss" in result
    ]
    return sorted(
        passing,
        key=lambda item: (
            -item["task_score"],
            item["validation_loss"],
            item["parameter_count"],
            item["training_seconds"],
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run bounded genetic architecture search using validation loss and task benchmarks"
    )
    parser.add_argument("--generations", type=int, default=3)
    parser.add_argument("--population", type=int, default=4)
    parser.add_argument("--elite-count", type=int, default=1)
    parser.add_argument("--steps", type=int, default=80)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--seq-len", type=int, default=24)
    parser.add_argument("--benchmark-tokens", type=int, default=64)
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--benchmark-data", type=Path, default=Path("data/benchmark.jsonl"))
    parser.add_argument("--checkpoint-dir", type=Path, default=Path("runs/evolution-candidates"))
    parser.add_argument("--out", type=Path, default=Path("runs/evolution-report.json"))
    parser.add_argument("--promote", action="store_true")
    parser.add_argument("--promoted-checkpoint", type=Path, default=Path("runs/klod-evolved.pt"))
    parser.add_argument("--overwrite-checkpoint", action="store_true")
    args = parser.parse_args()

    if not 1 <= args.generations <= 20:
        raise SystemExit("--generations must be between 1 and 20")
    if not 1 <= args.population <= 20:
        raise SystemExit("--population must be between 1 and 20")
    if not 1 <= args.elite_count <= args.population:
        raise SystemExit("--elite-count must be between 1 and population")
    if args.generations > 1 and args.elite_count >= args.population:
        raise SystemExit("For multiple generations, elite-count must be smaller than population")
    if not 1 <= args.steps <= 100000:
        raise SystemExit("--steps must be between 1 and 100000")
    if not 1 <= args.batch_size <= 128:
        raise SystemExit("--batch-size must be between 1 and 128")
    if not 8 <= args.seq_len <= 8192:
        raise SystemExit("--seq-len must be between 8 and 8192")
    if not 1 <= args.benchmark_tokens <= 256:
        raise SystemExit("--benchmark-tokens must be between 1 and 256")
    if not 10 <= args.timeout <= 600:
        raise SystemExit("--timeout must be between 10 and 600 seconds")
    if not args.data.is_file():
        raise SystemExit(f"Training corpus not found: {args.data}")
    if not args.benchmark_data.is_file():
        raise SystemExit(f"Benchmark dataset not found: {args.benchmark_data}")
    if args.data.resolve() == args.benchmark_data.resolve():
        raise SystemExit("Training corpus and benchmark dataset must be different files")
    if args.promote and args.promoted_checkpoint.exists() and not args.overwrite_checkpoint:
        raise SystemExit(
            f"Checkpoint already exists: {args.promoted_checkpoint}. "
            "Choose another path or pass --overwrite-checkpoint explicitly."
        )

    corpus = read_corpus(args.data)
    if len(ByteTokenizer().encode(corpus)) < args.seq_len * 2 + 10:
        raise SystemExit("Corpus is too small for a train/validation split at this sequence length")
    benchmark_cases = load_cases(args.benchmark_data)
    if not benchmark_cases:
        raise SystemExit("Benchmark dataset has no usable cases")

    args.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    population = build_candidates(args.population, args.seed)
    all_results = []
    generation_reports = []

    for generation in range(1, args.generations + 1):
        generation_results = []
        for candidate in population:
            result = evaluate(
                candidate,
                str(args.data.resolve()),
                str(args.benchmark_data.resolve()),
                args.steps,
                args.batch_size,
                args.seq_len,
                args.benchmark_tokens,
                args.timeout,
                str(args.checkpoint_dir.resolve()),
            )
            generation_results.append(result)
            all_results.append(result)

        ranked = rank_candidates(all_results)
        generation_reports.append({
            "generation": generation,
            "evaluated": len(generation_results),
            "passed": sum(bool(item.get("passed")) for item in generation_results),
            "best_candidate_so_far": ranked[0]["candidate"] if ranked else None,
            "best_task_score_so_far": ranked[0]["task_score"] if ranked else None,
            "best_validation_loss_so_far": ranked[0]["validation_loss"] if ranked else None,
        })

        if generation == args.generations or not ranked:
            break

        survivors = [Candidate(**item["config"]) for item in ranked[:args.elite_count]]
        offspring_count = args.population - len(survivors)
        parent_pool = ranked[:max(1, min(len(ranked), args.elite_count * 2))]
        next_population = []
        for index in range(offspring_count):
            parent_result = rng.choice(parent_pool)
            parent = Candidate(**parent_result["config"])
            child = mutate_candidate(
                parent,
                name=f"g{generation + 1}-candidate-{index + 1}",
                generation=generation + 1,
                rng=rng,
            )
            next_population.append(child)
        population = next_population

    ranked = rank_candidates(all_results)
    selected = ranked[0] if ranked else None
    report = {
        "generations": generation_reports,
        "results": all_results,
        "selected_candidate": selected.get("candidate") if selected else None,
        "selected_generation": selected.get("generation") if selected else None,
        "selected_task_score": selected.get("task_score") if selected else None,
        "selected_validation_loss": selected.get("validation_loss") if selected else None,
        "selected_checkpoint": selected.get("checkpoint") if selected else None,
        "selection_metric": "highest task_score (75% mean token F1 + 25% exact-match rate), then lowest held-out loss, fewer parameters and lower training time",
        "corpus": str(args.data),
        "benchmark_data": str(args.benchmark_data),
        "training_steps_per_candidate": args.steps,
        "architecture_evolution": "survivors are retained; offspring mutate width, heads, depth, experts, learning rate and dropout",
        "weight_inheritance": False,
        "automatic_promotion": False,
        "promoted": False,
        "limits": "Reference benchmarks are finite and can be overfit. Use fresh tests, human review and safety checks before promotion.",
    }

    if selected and args.promote:
        args.promoted_checkpoint.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(selected["checkpoint"], args.promoted_checkpoint)
        report["promoted"] = True
        report["promoted_checkpoint"] = str(args.promoted_checkpoint)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not selected:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
