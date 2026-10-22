import json

import pytest

from deta.data import read_licensed_jsonl, write_jsonl
from scripts.merge_training_manifests import merge_manifests


def test_merger_keeps_code_and_balances_first_party_instructions(tmp_path):
    code_path = tmp_path / "code.jsonl"
    instruction_path = tmp_path / "instructions.jsonl"
    output_path = tmp_path / "combined.jsonl"

    code_records = [{
        "content": "def add(left, right):\n    return left + right\n",
        "source_url": "https://github.com/example/project/blob/main/LICENSE",
        "license_id": "MIT",
        "source_type": "code",
        "source_name": "example",
        "path": "add.py",
    }]
    instruction_records = [{
        "content": "User: Olá\nAssistant: Que app você quer criar?\n",
        "source_url": "https://github.com/example/deta/blob/main/data/FIRST_PARTY_DATA_LICENSE.md",
        "license_id": "CC0-1.0",
        "source_type": "text",
        "source_name": "Deta instructions",
        "path": "dialogue/greeting",
    }]
    write_jsonl(iter(code_records), code_path)
    write_jsonl(iter(instruction_records), instruction_path)

    report = merge_manifests([code_path, instruction_path], output_path, instruction_repeats=3)
    merged = list(read_licensed_jsonl(output_path))
    assert report["code_records"] == 1
    assert report["instruction_records"] == 1
    assert report["instruction_repeats"] == 3
    assert len(merged) == 2
    assert merged[0]["source_type"] == "code"
    assert merged[1]["source_type"] == "text"
    assert merged[1]["content"].count("User: Olá") == 3
    assert len(merged[1]["content"]) > len(instruction_records[0]["content"])


def test_merger_rejects_missing_instruction_data(tmp_path):
    code_path = tmp_path / "code.jsonl"
    output_path = tmp_path / "out.jsonl"
    write_jsonl(iter([{
        "content": "print('hello')",
        "source_url": "https://github.com/example/project",
        "license_id": "MIT",
        "source_type": "code",
    }]), code_path)
    with pytest.raises(ValueError, match="instruction corpus"):
        merge_manifests([code_path], output_path)
