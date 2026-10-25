import argparse
import json
import random
import time
from pathlib import Path

import torch
from torch.nn import functional as F

from model import ForgeStudent, MAX_SEQ_LEN, encode

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "seed_examples.jsonl"
MODEL_DIR = ROOT / "models"


def read_examples(path, minimum=1):
    rows = []
    with Path(path).open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
                prompt, response = str(item["prompt"]).strip(), str(item["response"]).strip()
                if prompt and response:
                    rows.append({"prompt": prompt, "response": response})
            except (json.JSONDecodeError, KeyError, TypeError) as exc:
                raise ValueError("JSONL inválido na linha " + str(line_number) + ": " + str(exc)) from exc
    if len(rows) < minimum:
        raise ValueError("Corpus insuficiente: " + str(path))
    return rows


def make_stream(rows):
    text = "\n\n".join("Usuário: " + x["prompt"] + "\nAssistente: " + x["response"] for x in rows)
    return torch.tensor(encode(text, add_bos=True, add_eos=True), dtype=torch.long)


def sample_batch(stream, batch_size, device):
    if len(stream) < MAX_SEQ_LEN + 2:
        raise ValueError("O corpus precisa de mais tokens que a janela de contexto.")
    starts = torch.randint(0, len(stream) - MAX_SEQ_LEN - 1, (batch_size,))
    x = torch.stack([stream[s:s + MAX_SEQ_LEN] for s in starts])
    y = torch.stack([stream[s + 1:s + MAX_SEQ_LEN + 1] for s in starts])
    return x.to(device), y.to(device)


def evaluate(model, stream, device, batches=8):
    model.eval()
    maximum = len(stream) - MAX_SEQ_LEN - 1
    if maximum < 1:
        raise ValueError("O conjunto de validação é muito curto.")
    starts = torch.linspace(0, maximum, steps=min(batches, maximum + 1)).round().long().unique().tolist()
    losses = []
    with torch.no_grad():
        for start in starts:
            x = stream[start:start + MAX_SEQ_LEN].unsqueeze(0).to(device)
            y = stream[start + 1:start + MAX_SEQ_LEN + 1].unsqueeze(0).to(device)
            losses.append(float(F.cross_entropy(model(x).reshape(-1, 258), y.reshape(-1))))
    model.train()
    return sum(losses) / len(losses)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=DATA_PATH)
    parser.add_argument("--extra-data", type=Path, action="append", default=[])
    parser.add_argument("--steps", type=int, default=160)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=0.0007)
    parser.add_argument("--seed", type=int, default=20261025)
    parser.add_argument("--output", type=Path, default=MODEL_DIR / "motionforge-student.pt")
    args = parser.parse_args()
    if args.steps < 1 or args.batch_size < 1:
        raise ValueError("steps e batch-size precisam ser positivos")
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.set_num_threads(max(1, min(4, torch.get_num_threads())))
    examples, seen = [], set()
    for path in [args.data, *args.extra_data]:
        for item in read_examples(path):
            key = (item["prompt"].casefold(), item["response"].casefold())
            if key not in seen:
                seen.add(key)
                examples.append(item)
    if len(examples) < 5:
        raise ValueError("São necessários pelo menos cinco exemplos únicos.")
    random.shuffle(examples)
    split = max(1, int(len(examples) * 0.9))
    train_stream = make_stream(examples[:split])
    validation_stream = make_stream(examples[split:]) if len(examples[split:]) >= 1 else train_stream
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = ForgeStudent().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=0.01)
    initial_loss = evaluate(model, validation_stream, device, 4)
    started = time.time()
    for step in range(1, args.steps + 1):
        x, y = sample_batch(train_stream, args.batch_size, device)
        loss = F.cross_entropy(model(x).reshape(-1, 258), y.reshape(-1))
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        if step == 1 or step % 20 == 0 or step == args.steps:
            print("step=" + str(step) + "/" + str(args.steps) + " loss=" + format(loss.item(), ".4f"))
    final_loss = evaluate(model, validation_stream, device)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    metrics = {
        "status": "trained",
        "device": device,
        "parameters": sum(p.numel() for p in model.parameters()),
        "examples": len(examples),
        "initial_validation_loss": round(initial_loss, 4),
        "final_validation_loss": round(final_loss, 4),
        "loss_improved": final_loss < initial_loss,
        "training_seconds": round(time.time() - started, 2),
        "steps": args.steps,
        "checkpoint": str(args.output),
    }
    torch.save({
        "state_dict": model.cpu().state_dict(),
        "config": {"vocab_size": 258, "d_model": 48, "n_heads": 4, "n_layers": 12, "ff_dim": 92, "max_seq_len": 256},
        **{key: value for key, value in metrics.items() if key not in {"status", "device", "checkpoint"}},
        "seed": args.seed,
    }, args.output)
    metrics_path = args.output.with_suffix(".metrics.json")
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metrics, ensure_ascii=False))


if __name__ == "__main__":
    main()
