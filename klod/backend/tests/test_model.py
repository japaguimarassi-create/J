import torch
import pytest

from klod.neural import GPTModel, ModelConfig, expand_model


def test_forward_loss_and_backward() -> None:
    config = ModelConfig(vocab_size=300, max_seq_len=16, d_model=32, n_heads=4, n_layers=2, d_ff=64)
    model = GPTModel(config)
    tokens = torch.randint(0, config.vocab_size, (2, 12))
    logits, loss = model(tokens, tokens)
    assert logits.shape == (2, 12, config.vocab_size)
    assert loss is not None and torch.isfinite(loss)
    loss.backward()
    assert model.embedding.weight.grad is not None
    assert model.parameter_count() > 0


def test_generation_length() -> None:
    config = ModelConfig(vocab_size=300, max_seq_len=8, d_model=32, n_heads=4, n_layers=1, d_ff=64)
    output = GPTModel(config).generate(torch.randint(0, 300, (1, 5)), max_new_tokens=3)
    assert output.shape == (1, 8)


def test_odd_rope_head_dimension_rejected() -> None:
    with pytest.raises(ValueError):
        ModelConfig(vocab_size=300, d_model=27, n_heads=3)


def test_expansion_preserves_old_weights_and_initial_function() -> None:
    torch.manual_seed(7)
    source_config = ModelConfig(vocab_size=300, max_seq_len=16, d_model=32, n_heads=4, n_layers=2, d_ff=64)
    target_config = ModelConfig(vocab_size=360, max_seq_len=32, d_model=32, n_heads=4, n_layers=3, d_ff=96)
    source = GPTModel(source_config).eval()
    expanded, report = expand_model(source, target_config)
    expanded.eval()

    tokens = torch.randint(0, source_config.vocab_size, (2, 12))
    old_logits, _ = source(tokens)
    new_logits, _ = expanded(tokens)
    assert torch.allclose(old_logits, new_logits[:, :, :source_config.vocab_size], atol=1e-6, rtol=1e-5)
    assert torch.equal(source.embedding.weight, expanded.embedding.weight[:source_config.vocab_size])
    assert report.added_layers == 1
    assert report.added_vocabulary_items == 60
    assert report.expanded_parameters > report.previous_parameters


def test_expansion_refuses_architecture_breaking_width_change() -> None:
    source = GPTModel(ModelConfig(vocab_size=300, d_model=32, n_heads=4, n_layers=1, d_ff=64))
    target = ModelConfig(vocab_size=300, d_model=64, n_heads=4, n_layers=2, d_ff=128)
    with pytest.raises(ValueError):
        expand_model(source, target)

def test_next_token_targets_align_with_each_input_position() -> None:
    config = ModelConfig(vocab_size=300, max_seq_len=8, d_model=16, n_heads=2, n_layers=1, d_ff=32)
    model = GPTModel(config)
    tokens = torch.randint(0, config.vocab_size, (2, 5))
    targets = torch.randint(0, config.vocab_size, (2, 5))
    logits, loss = model(tokens, targets)
    expected = torch.nn.functional.cross_entropy(logits.reshape(-1, config.vocab_size), targets.reshape(-1))
    assert loss is not None
    assert torch.allclose(loss, expected)
