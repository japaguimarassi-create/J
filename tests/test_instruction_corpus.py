import json

from scripts.build_instruction_corpus import build_records
from deta.data import write_jsonl


def test_instruction_corpus_has_greetings_planning_and_debugging():
    records = build_records()
    contents = [item["content"] for item in records]
    assert len(records) >= 500
    assert len(contents) == len(set(contents))
    assert any("User: Olá\nAssistant:" in text for text in contents)
    assert any("Prepare a concise implementation plan" in text for text in contents)
    assert any("Reproduzir o problema" in text for text in contents)
    assert all(item["license_id"] == "CC0-1.0" for item in records)
    assert all(item["source_type"] == "text" for item in records)
    assert all(item["source_url"].startswith("https://github.com/") for item in records)
    assert not any("system prompt" in item["content"].lower() for item in records)


def test_instruction_corpus_does_not_train_a_fixed_self_description():
    contents = "\n".join(item["content"] for item in build_records()).lower()
    assert "i am deta" not in contents
    assert "sou a deta" not in contents
    assert "my name is" not in contents
