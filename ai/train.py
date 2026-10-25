from __future__ import annotations

import argparse
import json
import math
import random
import time
from pathlib import Path
from typing import Any

import torch
from torch.nn import functional as F

from ai.student import BLOCK_SIZE, BOS_ID, EOS_ID, EXPECTED_PARAMS, ForgeStudent, ByteBPETokenizer, UNK_ID, VOCAB_SIZE

ROOT = Path(__file__).resolve().parents[1]
SEED_PATH = ROOT / "data" / "seed.jsonl"
DEFAULT_OUTPUT = ROOT / "artifacts" / "student.pt"


def read_examples(paths: list[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for path_index, path in enumerate(paths):
        if not path.exists():
            if path_index == 0:
                raise FileNotFoundError("Corpus principal não encontrado: " + str(path))
            continue
        with path.open("r", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(str(path) + ":" + str(line_number) + ": JSON inválido") from exc
                if not isinstance(item, dict) or not isinstance(item.get("prompt"), str) or not isinstance(item.get("response"), str):
                    raise ValueError(str(path) + ":" + str(line_number) + ": cada exemplo precisa de prompt e response em texto")
                prompt, response = item["prompt"].strip(), item["response"].strip()
                if not prompt or not response:
                    continue
                key = (prompt.casefold(), response.casefold())
                if key not in seen:
                    seen.add(key)
                    rows.append({"prompt": prompt, "response": response})
    if len(rows) < 5:
        raise ValueError("São necessários pelo menos 5 exemplos únicos; corpus atual: " + str(len(rows)))
    return rows


def format_example(item: dict[str, str]) -> str:
    return "Usuário: " + item["prompt"] + "\nAssistente: " + item["response"]


def tokenize_examples(rows: list[dict[str, str]], tokenizer: ByteBPETokenizer) -> list[list[int]]:
    return [tokenizer.encode(format_example(item), add_special=True) for item in rows]


def make_stream(sequences: list[list[int]]) -> torch.Tensor:
    flattened: list[int] = []
    for sequence in sequences:
        flattened.extend(sequence)
    if len(flattened) < BLOCK_SIZE + 2:
        repeats = math.ceil((BLOCK_SIZE + 2) / max(1, len(flattened)))
        flattened *= repeats
    return torch.tensor(flattened, dtype=torch.long)


def sample_batch(stream: torch.Tensor, batch_size: int, device: str) -> tuple[torch.Tensor, torch.Tensor]:
    if stream.numel() < BLOCK_SIZE + 2:
        raise ValueError("Fluxo de treino menor que a janela do modelo.")
    maximum = stream.numel() - BLOCK_SIZE - 1
    starts = torch.randint(0, maximum + 1, (batch_size,))
    inputs = torch.stack([stream[int(start):int(start) + BLOCK_SIZE] for start in starts])
    targets = torch.stack([stream[int(start) + 1:int(start) + BLOCK_SIZE + 1] for start in starts])
    return inputs.to(device), targets.to(device)


def evaluate(model: ForgeStudent, sequences: list[list[int]], device: str) -> float:
    model.eval()
    total_loss = 0.0
    total_tokens = 0
    with torch.no_grad():
        for sequence in sequences:
            if len(sequence) < 2:
                continue
            ids = sequence[-(BLOCK_SIZE + 1):]
            tokens = torch.tensor(ids, dtype=torch.long, device=device)
            logits = model(tokens[:-1].unsqueeze(0))[0]
            labels = tokens[1:]
            loss_sum = F.cross_entropy(logits, labels, reduction="sum")
            total_loss += float(loss_sum.item())
            total_tokens += labels.numel()
    model.train()
    if total_tokens == 0:
        raise ValueError("Conjunto de validação sem tokens.")
    return total_loss / total_tokens


def train(args: argparse.Namespace) -> dict[str, Any]:
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.set_num_threads(max(1, min(4, torch.get_num_threads())))
    examples = read_examples(args.data)
    random.shuffle(examples)
    if len(examples) >= 8:
        validation_count = max(1, min(len(examples) - 5, int(round(len(examples) * 0.15))))
        train_examples, validation_examples = examples[:-validation_count], examples[-validation_count:]
    else:
        train_examples, validation_examples = examples, examples[-1:]
    training_texts = [format_example(item) for item in train_examples]
    tokenizer = ByteBPETokenizer.train(training_texts)
    train_sequences = tokenize_examples(train_examples, tokenizer)
    validation_sequences = tokenize_examples(validation_examples, tokenizer)
    stream = make_stream(train_sequences)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = ForgeStudent().to(device)
    parameter_count = model.count_parameters()
    if parameter_count != EXPECTED_PARAMS:
        raise RuntimeError("Contagem de parâmetros divergente: " + str(parameter_count))
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=0.01)
    initial_loss = evaluate(model, validation_sequences, device)
    steps_per_epoch = max(2, min(16, math.ceil(stream.numel() / (BLOCK_SIZE * args.batch_size))))
    total_steps = args.steps if args.steps > 0 else steps_per_epoch * args.epochs
    started = time.time()
    losses: list[float] = []
    for step in range(1, total_steps + 1):
        inputs, targets = sample_batch(stream, args.batch_size, device)
        logits = model(inputs)
        loss = F.cross_entropy(logits.reshape(-1, VOCAB_SIZE), targets.reshape(-1))
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        losses.append(float(loss.item()))
        if step == 1 or step % 10 == 0 or step == total_steps:
            print("step=" + str(step) + "/" + str(total_steps) + " loss=" + format(loss.item(), ".4f"), flush=True)
    final_loss = evaluate(model, validation_sequences, device)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    metrics: dict[str, Any] = {
        "status": "trained",
        "architecture": "12M? no; 2-layer causal Transformer, 32 hidden, tied 7k BPE embeddings",
        "device": device,
        "parameters": parameter_count,
        "expected_parameters": EXPECTED_PARAMS,
        "parameter_count_valid": parameter_count == EXPECTED_PARAMS,
        "vocabulary_size": VOCAB_SIZE,
        "context_tokens": BLOCK_SIZE,
        "examples": len(examples),
        "train_examples": len(train_examples),
        "validation_examples": len(validation_examples),
        "initial_validation_loss": round(initial_loss, 5),
        "final_validation_loss": round(final_loss, 5),
        "loss_improved": final_loss < initial_loss,
        "mean_final_training_loss": round(sum(losses[-min(10, len(losses)):]) / min(10, len(losses)), 5),
        "training_steps": total_steps,
        "epochs_requested": args.epochs,
        "training_seconds": round(time.time() - started, 2),
        "checkpoint": str(args.out),
        "teacher_examples_included": sum(1 for item in examples if "three-teacher-consensus" in str(item.get("source", ""))),
    }
    bundle = {
        "model_state": model.cpu().state_dict(),
        "tokenizer": tokenizer.to_dict(),
        "metrics": metrics,
        "seed": args.seed,
    }
    torch.save(bundle, args.out)
    metrics_path = args.out.with_suffix(".metrics.json")
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metrics, ensure_ascii=False), flush=True)
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Treina o aluno MotionForge de exatamente 249.984 parâmetros.")
    parser.add_argument("--data", action="append", type=Path, default=None, help="JSONL do corpus; pode ser repetido. O primeiro arquivo é obrigatório.")
    parser.add_argument("--out", "--output", dest="out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--steps", type=int, default=0, help="Opcional: substitui a quantidade calculada por época.")
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--learning-rate", type=float, default=0.001)
    parser.add_argument("--seed", type=int, default=20261025)
    args = parser.parse_args()
    args.data = args.data or [SEED_PATH, ROOT / "data" / "distilled.jsonl"]
    if args.epochs < 1 or args.epochs > 30 or args.steps < 0 or args.batch_size < 1 or args.batch_size > 16:
        raise ValueError("epochs deve ser 1-30; steps >= 0; batch-size deve ser 1-16.")
    train(args)


if __name__ == "__main__":
    main()
