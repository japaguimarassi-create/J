from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--through", type=int, choices=range(1, 13), default=12)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    evidence_path = root / "docs" / "release-evidence.json"
    if not evidence_path.is_file():
        print("Release evidence file is missing.", file=sys.stderr)
        return 2

    try:
        payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"Release evidence cannot be read: {error}", file=sys.stderr)
        return 2

    confirmations = payload.get("confirmations")
    if not isinstance(confirmations, list) or len(confirmations) != 12:
        print("Exactly twelve confirmations must be recorded.", file=sys.stderr)
        return 2

    minimum = float(payload.get("minimum_score_per_confirmation", 8.0))
    average_minimum = float(payload.get("minimum_average_score", 8.5))
    selected = confirmations[:args.through]
    scores: list[float] = []
    errors: list[str] = []

    for expected_id, item in enumerate(selected, start=1):
        if not isinstance(item, dict) or item.get("id") != expected_id:
            errors.append(f"Confirmation {expected_id}: invalid record or order.")
            continue
        name = item.get("name", f"Confirmation {expected_id}")
        score = item.get("score")
        refs = item.get("evidence")
        if item.get("status") != "pass":
            errors.append(f"{expected_id}. {name}: status is not pass.")
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            errors.append(f"{expected_id}. {name}: numeric score is missing.")
        elif float(score) < minimum:
            errors.append(f"{expected_id}. {name}: score {score} is below {minimum:.1f}.")
        else:
            scores.append(float(score))
        if not isinstance(refs, list) or not refs or not all(isinstance(ref, str) and ref.strip() for ref in refs):
            errors.append(f"{expected_id}. {name}: evidence references are missing.")

    if len(scores) == args.through:
        average = sum(scores) / len(scores)
        if average < average_minimum:
            errors.append(f"Average {average:.2f} is below {average_minimum:.2f}.")
    else:
        average = 0.0

    if errors:
        print(f"Release gate blocked: {len(errors)} issue(s).")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Release gate passed through confirmation {args.through}.")
    print(f"Average score: {average:.2f}/10.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
