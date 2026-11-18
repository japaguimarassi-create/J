import torch

from klod.neural import GPTModel, ModelConfig


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
    try:
        ModelConfig(vocab_size=300, d_model=27, n_heads=3)
    except ValueError:
        return
    raise AssertionError("Odd RoPE head dimensions must be rejected")
