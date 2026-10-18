from __future__ import annotations

import argparse
import json
from pathlib import Path

from socializer.core import validate_messages


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("file", nargs="?", default="data/social_dialogues.jsonl")
    args = parser.parse_args()
    path = Path(args.file)
    if not path.exists():
        print(f"Arquivo não encontrado: {path}")
        return 2
    valid = 0
    invalid = 0
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                print(f"linha {line_number}: JSON inválido: {exc}")
                invalid += 1
                continue
            ok, message = validate_messages(row.get("messages"))
            if ok:
                valid += 1
            else:
                print(f"linha {line_number}: {message}")
                invalid += 1
    print(f"Válidos: {valid} | Inválidos: {invalid}")
    return 0 if invalid == 0 and valid > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
