import tempfile

import pytest
import torch

from klod.model import ByteTokenizer, KlodModel, ModelConfig
from klod.tools import analyze_file, create_file


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
