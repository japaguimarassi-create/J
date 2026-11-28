import json
import tempfile
import zipfile
from pathlib import Path

import pytest
import torch

from klod.code_tools import validate_code
from klod.memory import ConversationMemory
from klod.model import ByteTokenizer, KlodModel, ModelConfig
from klod.tools import analyze_file, create_file
from klod.train import read_corpus, mean_loss


def test_byte_tokenizer_roundtrip():
    tokenizer = ByteTokenizer()
    text = "KLOD: olá, mundo!"
    assert tokenizer.decode(tokenizer.encode(text)) == text


def test_model_forward_and_loss():
    model = KlodModel(ModelConfig(d_model=32, n_heads=4, n_layers=2, n_experts=2, max_seq_len=16, dropout=0))
    inputs = torch.randint(2, 258, (2, 16))
    targets = torch.randint(2, 258, (2, 16))
    logits, loss = model(inputs, targets)
    assert logits.shape == (2, 16, 258)
    assert loss is not None and torch.isfinite(loss)


def test_workspace_file_tools():
    with tempfile.TemporaryDirectory() as directory:
        created = create_file(directory, "src/main.py", "print('ok')")
        assert created["created"] is True
        result = analyze_file(directory, "src/main.py")
        assert result["is_text"] is True
        assert result["lines"] == 1
        with pytest.raises(FileExistsError):
            create_file(directory, "src/main.py", "changed")


def test_workspace_blocks_path_traversal():
    with tempfile.TemporaryDirectory() as directory:
        with pytest.raises(PermissionError):
            create_file(directory, "../outside.txt", "blocked")


def test_config_rejects_invalid_head_width():
    with pytest.raises(ValueError):
        KlodModel(ModelConfig(d_model=30, n_heads=4))


def test_conversation_memory_is_persistent_and_bounded():
    with tempfile.TemporaryDirectory() as directory:
        memory = ConversationMemory(Path(directory) / "memory.sqlite3", max_messages_per_conversation=10)
        memory.add("test-thread", "user", "primeira")
        memory.add("test-thread", "assistant", "resposta")
        assert [item["content"] for item in memory.recent("test-thread")] == ["primeira", "resposta"]
        assert memory.clear("test-thread") == 2
        assert memory.recent("test-thread") == []


def test_python_code_static_validation():
    with tempfile.TemporaryDirectory() as directory:
        create_file(directory, "valid.py", "def add(a, b):\n    return a + b\n")
        assert validate_code(directory, "valid.py")["valid"] is True
        create_file(directory, "invalid.py", "def broken(:\n")
        assert validate_code(directory, "invalid.py")["valid"] is False


def test_json_and_zip_static_validation():
    with tempfile.TemporaryDirectory() as directory:
        create_file(directory, "config.json", json.dumps({"ok": True}))
        assert validate_code(directory, "config.json")["valid"] is True
        archive_path = Path(directory) / "mod.jar"
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\n")
            archive.writestr("example/Mod.class", b"class-data")
        result = validate_code(directory, "mod.jar")
        assert result["valid"] is True
        assert result["has_manifest"] is True
        assert result["entries"] == 2


def test_benchmark_metrics():
    from klod.benchmarks import normalize, token_f1

    assert normalize("  Olá   Mundo ") == "olá mundo"
    assert token_f1("a + b", "a + b") == 1.0
    assert token_f1("a", "b") == 0.0


def test_training_loader_supports_chat_jsonl():
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "chat.jsonl"
        path.write_text(
            json.dumps({
                "messages": [
                    {"role": "user", "content": "Olá"},
                    {"role": "assistant", "content": "Oi"},
                ]
            }) + "\n" + json.dumps({
                "prompt": "Some 2 + 2",
                "completion": "4",
            }),
            encoding="utf-8",
        )
        corpus = read_corpus(path)
        assert "Usuário: Olá" in corpus
        assert "KLOD: Oi" in corpus
        assert "Usuário: Some 2 + 2" in corpus


def test_validation_loss_is_finite():
    config = ModelConfig(d_model=32, n_heads=4, n_layers=1, n_experts=2, max_seq_len=12, dropout=0)
    model = KlodModel(config)
    data = torch.randint(2, 258, (80,), dtype=torch.long)
    loss = mean_loss(model, data, seq_len=12)
    assert isinstance(loss, float)
    assert loss > 0
