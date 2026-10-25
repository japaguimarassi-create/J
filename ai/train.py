from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as F

from ai.student import BLOCK_SIZE, EXPECTED_PARAMS, PAD_ID, ByteBPETokenizer, ForgeStudent

ROOT = Path(__file__).resolve().parents[1]


def read_examples(paths: list[str], max_samples: int) -> list[dict[str, str]]:
    examples: list[dict[str, str]] = []
    for raw_path in paths:
        path = Path(raw_path)
        if not path.is_absolute():
            path = ROOT / path
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            prompt, response = str(item.get("prompt", "")).strip(), str(item.get("response", "")).strip()
            if prompt and response:
                examples.append({"prompt":prompt[:12000],"response":response[:12000]})
                if len(examples) >= max_samples:
                    return examples
    return examples


def make_windows(examples: list[dict[str, str]], tokenizer: ByteBPETokenizer) -> list[torch.Tensor]:
    windows: list[torch.Tensor] = []
    window_tokens = BLOCK_SIZE + 1
    for item in examples:
        text = "Usuário: " + item["prompt"] + "\nForge AI: " + item["response"] + "\n"
        ids = tokenizer.encode(text, add_special=True)
        if len(ids) < 2:
            continue
        for start in range(0, max(1, len(ids) - 1), max(64, BLOCK_SIZE // 2)):
            part = ids[start:start + window_tokens]
            if len(part) < 2:
                continue
            part += [PAD_ID] * (window_tokens - len(part))
            windows.append(torch.tensor(part, dtype=torch.long))
    return windows


def train(args: argparse.Namespace) -> dict[str, Any]:
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    examples = read_examples(args.data, args.max_samples)
    if len(examples) < 2:
        raise SystemExit("Dataset insuficiente: forneça pelo menos 2 exemplos com prompt e response.")
    texts = ["Usuário: " + item["prompt"] + "\nForge AI: " + item["response"] + "\n" for item in examples]
    tokenizer = ByteBPETokenizer.train(texts)
    windows = make_windows(examples, tokenizer)
    if not windows:
        raise SystemExit("Nenhuma janela de treinamento válida.")
    model = ForgeStudent()
    count = model.count_parameters()
    if count != EXPECTED_PARAMS:
        raise SystemExit("Arquitetura inválida: " + str(count) + " parâmetros; esperado " + str(EXPECTED_PARAMS))
    device_name = args.device
    if device_name == "auto":
        device_name = "cuda" if torch.cuda.is_available() else "cpu"
    if device_name == "cuda" and not torch.cuda.is_available():
        raise SystemExit("CUDA solicitado, mas não está disponível.")
    device = torch.device(device_name)
    model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=0.01)
    history: list[float] = []
    model.train()
    for epoch in range(args.epochs):
        order = list(range(len(windows)))
        random.shuffle(order)
        total_loss, batches = 0.0, 0
        for batch_start in range(0, len(order), args.batch_size):
            indices = order[batch_start:batch_start + args.batch_size]
            batch = torch.stack([windows[index] for index in indices]).to(device)
            x, targets = batch[:, :-1], batch[:, 1:].clone()
            targets[targets == PAD_ID] = -100
            logits = model(x)
            loss = F.cross_entropy(logits.reshape(-1, logits.size(-1)), targets.reshape(-1), ignore_index=-100)
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            total_loss += float(loss.detach().cpu())
            batches += 1
        average = total_loss / max(1, batches)
        history.append(average)
        print("epoch", epoch + 1, "of", args.epochs, "loss", round(average, 4), "windows", len(windows))
    output = Path(args.out)
    if not output.is_absolute():
        output = ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"model_state":model.cpu().state_dict(),"tokenizer":tokenizer.to_dict(),"metadata":{
        "architecture":"MotionForge ForgeStudent","trainable_parameters":count,"examples":len(examples),
        "windows":len(windows),"epochs":args.epochs,"loss_history":history,"seed":args.seed,
        "note":"Small task-specific student; quality depends on dataset quality and evaluation."
    }}, output)
    return {"output":str(output),"parameters":count,"examples":len(examples),"windows":len(windows),"epochs":args.epochs,"loss_history":history}


def main() -> None:
    parser = argparse.ArgumentParser(description="Treina o aluno local de 249.984 parâmetros do MotionForge.")
    parser.add_argument("--data", action="append", default=[], help="Dataset JSONL; a opção pode se repetir.")
    parser.add_argument("--out", default="artifacts/student.pt")
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--max-samples", type=int, default=4000)
    parser.add_argument("--learning-rate", type=float, default=0.0004)
    parser.add_argument("--device", choices=["auto","cpu","cuda"], default="auto")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    args.epochs = max(1, min(30, args.epochs))
    args.batch_size = max(1, min(32, args.batch_size))
    args.max_samples = max(2, min(20000, args.max_samples))
    args.data = args.data or ["data/seed.jsonl","data/distilled.jsonl"]
    print(json.dumps(train(args), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
