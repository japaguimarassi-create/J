import argparse
import ast
import hashlib
import json
import re
from pathlib import Path

import torch
from torch.nn import functional as F

from model import HyperInterNetwork
from tokenizer import load_tokenizer


def answer_loss(logits, targets, first_answer_token):
    start = max(0, first_answer_token - 1)
    if start >= targets.size(1):
        return float("nan")
    return F.cross_entropy(
        logits[:, start:, :].reshape(-1, logits.size(-1)),
        targets[:, start:].reshape(-1),
    ).item()


def python_syntax_ok(source):
    try:
        tree = ast.parse(source)
        return any(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            for node in ast.walk(tree)
        )
    except SyntaxError:
        return False


def balanced_delimiters(source):
    pairs = {")": "(", "]": "[", "}": "{"}
    opening = set(pairs.values())
    stack = []
    quote = None
    escaped = False
    for char in source:
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in ("'", '"', chr(96)):
            quote = char
        elif char in opening:
            stack.append(char)
        elif char in pairs:
            if not stack or stack.pop() != pairs[char]:
                return False
    return not stack and quote is None


def validate_candidate(language, source):
    if not re.search(r"[A-Za-z0-9_]", source):
        return False
    if language == "python":
        return python_syntax_ok(source)
    if language == "html":
        lowered = source.lower()
        return "<html" in lowered and "</html>" in lowered and "<h1" in lowered
    if language == "javascript":
        return bool(re.search(r"\b(function|const|let|return)\b", source)) and balanced_delimiters(source)
    if language == "lua":
        return bool(re.search(r"\b(function|local|return|for|while)\b", source)) and balanced_delimiters(source)
    if language in ("java", "csharp", "cpp"):
        return bool(re.search(r"\b(static|class|int|bool|boolean|return|void)\b", source)) and balanced_delimiters(source)
    return balanced_delimiters(source)


def load_tasks(path):
    tasks = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            tasks.append(json.loads(line))
    if not tasks:
        raise ValueError("Benchmark file is empty.")
    return tasks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--tasks", type=Path, default=Path(__file__).with_name("coding_benchmark.jsonl"))
    parser.add_argument("--tokenizer-json", type=Path)
    parser.add_argument("--output", type=Path, default=Path("benchmark-results"))
    parser.add_argument("--generate", action="store_true")
    parser.add_argument("--max-new-tokens", type=int, default=48)
    args = parser.parse_args()

    checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    config = dict(checkpoint["config"])
    tokenizer = load_tokenizer(args.tokenizer_json)
    if tokenizer.vocab_size != config["vocab_size"]:
        raise ValueError("Evaluation tokenizer vocabulary does not match the checkpoint.")
    tokenizer_sha256 = (
        hashlib.sha256(Path(args.tokenizer_json).read_bytes()).hexdigest()
        if args.tokenizer_json else "procedural-byte-v1"
    )
    if checkpoint.get("tokenizer_sha256", "procedural-byte-v1") != tokenizer_sha256:
        raise ValueError("Evaluation tokenizer fingerprint does not match the checkpoint.")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    is_target = (
        config.get("experts") == 7
        and config.get("expert_layers") == 10
        and config.get("expert_width") == 256
        and config.get("fusion_layers") == 20
        and config.get("fusion_width") == 1792
    )
    if is_target and device.type != "cuda":
        raise RuntimeError("Target evaluation requires CUDA; refusing a CPU substitute.")
    if is_target and not torch.cuda.is_bf16_supported():
        raise RuntimeError("Target evaluation requires CUDA BF16 support.")
    use_bf16 = device.type == "cuda" and torch.cuda.is_bf16_supported()
    model = HyperInterNetwork(**config).to(device)
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()
    tasks = load_tasks(args.tasks)
    args.output.mkdir(parents=True, exist_ok=True)

    totals = {"collective_nll": 0.0, "expert_nll": [0.0] * 7, "count": 0}
    candidates_path = args.output / "candidates.jsonl"
    with candidates_path.open("w", encoding="utf-8") as candidate_file:
        for task_index, task in enumerate(tasks):
            prompt = task["prompt"]
            reference = task["reference"]
            prompt_ids = tokenizer.encode(prompt, add_special_tokens=False)
            reference_ids = tokenizer.encode(reference, add_special_tokens=False)
            full_ids = [
                tokenizer.bos_id,
                *prompt_ids,
                *reference_ids,
                tokenizer.eos_id,
            ]
            prompt_token_count = len(prompt_ids)
            model_input = torch.tensor([full_ids[:-1]], dtype=torch.long, device=device)
            targets = torch.tensor([full_ids[1:]], dtype=torch.long, device=device)
            if model_input.size(1) > model.context_length:
                raise ValueError(f"Benchmark task {task_index} exceeds model context length.")
            answer_start = 1 + max(0, prompt_token_count)
            with torch.no_grad(), torch.autocast(
                device_type=device.type,
                dtype=torch.bfloat16 if use_bf16 else torch.float16,
                enabled=device.type == "cuda",
            ):
                final_logits, auxiliary_logits = model(model_input, return_aux=True)
            collective_score = answer_loss(final_logits, targets, answer_start)
            expert_scores = [
                answer_loss(auxiliary_logits[:, index], targets, answer_start)
                for index in range(7)
            ]
            totals["collective_nll"] += collective_score
            for index, score in enumerate(expert_scores):
                totals["expert_nll"][index] += score
            totals["count"] += 1

            task_output = {
                "task_index": task_index,
                "language": task["language"],
                "collective_reference_nll": collective_score,
                "expert_reference_nll": expert_scores,
            }
            if args.generate:
                prefix = torch.tensor([[1, *prompt_ids]], dtype=torch.long, device=device)
                with torch.no_grad(), torch.autocast(
                    device_type=device.type,
                    dtype=torch.bfloat16 if use_bf16 else torch.float16,
                    enabled=device.type == "cuda",
                ):
                    generated = model.generate_all(
                        prefix,
                        max_new_tokens=args.max_new_tokens,
                        temperature=0.0,
                    )
                decoded = [
                    tokenizer.decode(sequence[0, prefix.size(1):].tolist())
                    for sequence in generated
                ]
                labels = ["collective"] + [f"network_{index + 1}" for index in range(7)]
                task_output["candidates"] = [
                    {
                        "candidate": label,
                        "code": code,
                        "syntax_ok": validate_candidate(task["language"], code),
                    }
                    for label, code in zip(labels, decoded)
                ]
                candidate_file.write(
                    json.dumps({**task_output, "reference": reference}, ensure_ascii=False) + "\n"
                )
            else:
                candidate_file.write(json.dumps(task_output, ensure_ascii=False) + "\n")

    count = totals["count"]
    report = {
        "checkpoint": str(args.checkpoint),
        "device": str(device),
        "bf16": use_bf16,
        "tokenizer_sha256": tokenizer_sha256,
        "tasks": count,
        "collective_mean_nll": totals["collective_nll"] / count,
        "expert_mean_nll": [value / count for value in totals["expert_nll"]],
        "generation_enabled": args.generate,
        "candidate_file": str(candidates_path),
        "interpretation": "Lower reference NLL is better. Syntax checks are not proof of semantic correctness.",
    }
    (args.output / "summary.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
