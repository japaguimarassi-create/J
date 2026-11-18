from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from urllib.parse import urlparse

MINIMUM_SCORE = 8.0
MINIMUM_AVERAGE_SCORE = 8.5
CONFIRMATION_COUNT = 12
REPOSITORY = "japaguimarassi-create/J"


def evaluate_payload(payload: object, through: int = CONFIRMATION_COUNT) -> tuple[list[str], float]:
    errors: list[str] = []
    if isinstance(through, bool) or not isinstance(through, int) or not 1 <= through <= CONFIRMATION_COUNT:
        return ["The requested release-gate range is invalid."], 0.0
    if not isinstance(payload, dict):
        return ["Release evidence must be a JSON object."], 0.0

    confirmations = payload.get("confirmations")
    if not isinstance(confirmations, list) or len(confirmations) != CONFIRMATION_COUNT:
        return ["Exactly twelve confirmations must be recorded."], 0.0

    scores: list[float] = []
    for expected_id, item in enumerate(confirmations[:through], start=1):
        if not isinstance(item, dict) or item.get("id") != expected_id:
            errors.append(f"Confirmation {expected_id}: invalid record or order.")
            continue

        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            name = f"Confirmation {expected_id}"

        if item.get("status") != "pass":
            errors.append(f"{expected_id}. {name}: status is not pass.")

        score = item.get("score")
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            errors.append(f"{expected_id}. {name}: numeric score is missing.")
        elif not math.isfinite(float(score)) or not 0.0 <= float(score) <= 10.0:
            errors.append(f"{expected_id}. {name}: score must be finite and between 0 and 10.")
        elif float(score) < MINIMUM_SCORE:
            errors.append(f"{expected_id}. {name}: score {score} is below {MINIMUM_SCORE:.1f}.")
        else:
            scores.append(float(score))

        refs = item.get("evidence")
        if not isinstance(refs, list) or not refs:
            errors.append(f"{expected_id}. {name}: evidence references are missing.")
            continue

        for reference in refs:
            if not isinstance(reference, str) or not reference.strip():
                errors.append(f"{expected_id}. {name}: evidence reference is invalid.")
                continue
            parsed = urlparse(reference.strip())
            if parsed.scheme != "https" or parsed.netloc != "github.com" or not parsed.path.startswith("/" + REPOSITORY + "/"):
                errors.append(f"{expected_id}. {name}: evidence must link to this repository's GitHub record.")
                break

    average = sum(scores) / len(scores) if len(scores) == through else 0.0
    if len(scores) == through and average < MINIMUM_AVERAGE_SCORE:
        errors.append(f"Average {average:.2f} is below {MINIMUM_AVERAGE_SCORE:.2f}.")

    return errors, average


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--through", type=int, choices=range(1, CONFIRMATION_COUNT + 1), default=CONFIRMATION_COUNT)
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

    errors, average = evaluate_payload(payload, args.through)
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
