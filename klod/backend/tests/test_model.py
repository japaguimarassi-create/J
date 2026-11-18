import torch
from klod_core.model import KlodLM

def test_forward_loss_and_parameter_count():
    model = KlodLM(vocab_size=300, width=32, layers=2, heads=4, expansion=64)
    tokens = torch.randint(0, 300, (2, 16))
    logits, loss = model(tokens, tokens)
    assert logits.shape == (2, 16, 300)
    assert loss is not None and torch.isfinite(loss)
    assert model.parameter_count == sum(p.numel() for p in model.parameters())
