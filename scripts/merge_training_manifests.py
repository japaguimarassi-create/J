import argparse
import json
from pathlib import Path
from typing import Iterable

from deta.data import read_licensed_jsonl, write_jsonl


def merge_manifests(
    input_paths: Iterable[str | Path],
    output_path: str | Path,
    instruction_repeats: int = 3,
) -> dict[str, int]:
    if instruction_repeats < 1 or instruction_repeats > 8:
        raise ValueError("instruction_repeats must be between 1 and 8")
    code_records = []
    instruction_text = []
    instruction_source = ""
    text_records = 0
    for input_path in input_paths:
        for record in read_licensed_jsonl(input_path):
            if record["source_type"] == "text":
                instruction_text.append(record["content"].strip())
                instruction_source = record["source_url"]
                text_records += 1
            else:
                code_records.append(record)

    if not code_records:
        raise ValueError("The combined manifest needs approved code records.")
    if not instruction_text:
        raise ValueError("The combined manifest needs the instruction corpus.")

    bundled_instruction = ("\n\n".join(instruction_text) + "\n\n") * instruction_repeats
    instruction_bundle = {
        "content": bundled_instruction,
        "source_url": instruction_source,
        "license_id": "CC0-1.0",
        "source_type": "text",
        "source_name": "Deta first-party CC0 instruction corpus; repetition for fine-tuning balance",
        "path": "data/instruction.jsonl",
    }
    records = code_records + [instruction_bundle]
    count = write_jsonl(iter(records), output_path)
    return {
        "code_records": len(code_records),
        "instruction_records": text_records,
        "instruction_repeats": instruction_repeats,
        "combined_records": count,
        "instruction_bytes": len(bundled_instruction.encode("utf-8")),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge approved code and instruction records for Deta fine-tuning.")
    parser.add_argument("--inputs", nargs="+", required=True)
    parser.add_argument("--output", type=Path, default=Path("data/deta-training-v2.jsonl"))
    parser.add_argument("--instruction-repeats", type=int, default=3)
    args = parser.parse_args()
    report = merge_manifests(args.inputs, args.output, args.instruction_repeats)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
