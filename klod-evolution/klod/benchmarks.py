import argparse
import json
import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

from .runtime import KlodRuntime


def normalize(text: str) -> str:
    return " ".join(text.strip().casefold().split())


def token_f1(prediction: str, expected: str) -> float:
    predicted = Counter(re.findall(r"\w+|[^\w\s]", prediction.casefold()))
    reference = Counter(re.findall(r"\w+|[^\w\s]", expected.casefold()))
    overlap = sum((predicted & reference).values())
    if not predicted or not reference:
        return float(predicted == reference)
    precision = overlap / sum(predicted.values())
    recall = overlap / sum(reference.values())
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def load_cases(path: Path) -> list[dict]:
    cases = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        item = json.loads(line)
        if not isinstance(item.get("prompt"), str) or not isinstance(item.get("expected"), str):
            raise ValueError(f"Line {line_number} must contain string prompt and expected fields")
        cases.append({
            "id": str(item.get("id", line_number)),
            "category": str(item.get("category", "general")),
            "prompt": item["prompt"],
            "expected": item["expected"],
        })
    if not cases:
        raise ValueError("Benchmark dataset is empty")
    return cases


def run_benchmark(checkpoint: str, dataset: Path, max_new_tokens: int = 256) -> dict:
    runtime = KlodRuntime(checkpoint)
    cases = load_cases(dataset)
    results = []
    category_scores = defaultdict(list)

    for case in cases:
        prediction = runtime.chat(case["prompt"], max_new_tokens=max_new_tokens)
        expected = case["expected"]
        score = {
            "id": case["id"],
            "category": case["category"],
            "exact_match": normalize(prediction) == normalize(expected),
            "character_similarity": SequenceMatcher(
                None,
                normalize(prediction),
                normalize(expected),
            ).ratio(),
            "token_f1": token_f1(prediction, expected),
            "prediction": prediction,
            "expected": expected,
        }
        results.append(score)
        category_scores[case["category"]].append(score["token_f1"])

    return {
        "checkpoint": str(checkpoint),
        "dataset": str(dataset),
        "cases": len(results),
        "exact_match_rate": sum(item["exact_match"] for item in results) / len(results),
        "mean_character_similarity": sum(item["character_similarity"] for item in results) / len(results),
        "mean_token_f1": sum(item["token_f1"] for item in results) / len(results),
        "category_token_f1": {
            category: sum(scores) / len(scores)
            for category, scores in sorted(category_scores.items())
        },
        "results": results,
        "warning": "Scores measure similarity to this reference set, not general intelligence or safety.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate a KLOD checkpoint against reference tasks")
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("runs/benchmark-report.json"))
    parser.add_argument("--max-new-tokens", type=int, default=256)
    args = parser.parse_args()

    if not 1 <= args.max_new_tokens <= 2048:
        raise SystemExit("--max-new-tokens must be between 1 and 2048")
    report = run_benchmark(args.checkpoint, args.data, args.max_new_tokens)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "results"}, indent=2))


if __name__ == "__main__":
    main()
