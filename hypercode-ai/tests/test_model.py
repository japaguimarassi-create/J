import sys
from pathlib import Path

import torch
from torch.nn import functional as F

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "training"))

from model import HyperInterNetwork, smoke_config, target_config
from tokenizer import ProceduralTokenizer, WORD_SYSTEMS, CODE_SYSTEMS


def test_target_dimensions():
    config = target_config()
    assert config["experts"] == 7
    assert config["expert_layers"] == 10
    assert config["expert_width"] == 256
    assert config["fusion_layers"] == 20
    assert config["fusion_width"] == 1792
    assert config["experts"] * config["expert_layers"] * config["expert_width"] == 17920
    assert config["fusion_layers"] * config["fusion_width"] == 35840
    assert 35840 == 2 * 17920


def test_all_networks_process_same_input_and_produce_outputs():
    torch.manual_seed(1)
    model = HyperInterNetwork(**smoke_config())
    calls = [0] * 7
    handles = []
    for index in range(7):
        def hook(module, args, output, index=index):
            calls[index] += 1
        handles.append(model.experts[index][0].register_forward_hook(hook))
    tokens = torch.randint(4, 260, (2, 24))
    final_logits, expert_logits = model(tokens, return_aux=True)
    for handle in handles:
        handle.remove()
    assert calls == [1] * 7
    assert final_logits.shape == (2, 24, 260)
    assert expert_logits.shape == (2, 7, 24, 260)


def test_mutual_communication_crosses_between_networks():
    torch.manual_seed(2)
    model = HyperInterNetwork(**smoke_config())
    communication = model.communication[0].eval()
    states = torch.randn(2, 7, 5, 32)
    baseline = communication(states)
    changed = states.clone()
    changed[:, 0] += torch.linspace(-3.0, 3.0, 32).view(1, 1, 32)
    after_change = communication(changed)
    assert not torch.allclose(baseline[:, 1], after_change[:, 1])
    assert not torch.allclose(baseline[:, 6], after_change[:, 6])


def test_gradients_reach_all_networks_communication_and_core():
    torch.manual_seed(3)
    model = HyperInterNetwork(**smoke_config())
    tokens = torch.randint(4, 260, (2, 20))
    labels = torch.randint(4, 260, (2, 20))
    final_logits, expert_logits = model(tokens, return_aux=True)
    loss = F.cross_entropy(final_logits.reshape(-1, 260), labels.reshape(-1))
    loss = loss + sum(
        F.cross_entropy(expert_logits[:, index].reshape(-1, 260), labels.reshape(-1))
        for index in range(7)
    ) / 7
    loss.backward()
    for expert in model.experts:
        assert all(block.attention.qkv.weight.grad is not None for block in expert)
    assert model.communication[0].qkv.weight.grad is not None
    assert model.fusion_blocks[0].attention.qkv.weight.grad is not None


def test_causal_attention_does_not_see_future_tokens():
    torch.manual_seed(4)
    model = HyperInterNetwork(**smoke_config()).eval()
    first = torch.randint(4, 260, (1, 12))
    second = first.clone()
    second[:, 8:] = torch.randint(4, 260, (1, 4))
    with torch.no_grad():
        first_logits = model(first)
        second_logits = model(second)
    assert torch.allclose(first_logits[:, :8], second_logits[:, :8], atol=1e-5, rtol=1e-5)


def test_tokenizer_has_twelve_stages_and_uses_first_sentence_language():
    tokenizer = ProceduralTokenizer()
    assert len(WORD_SYSTEMS) == 12
    assert len(CODE_SYSTEMS) == 12
    analysis = tokenizer.analyze("Olá, como você está? The code uses a function.", code=False)
    assert analysis["dictionary_language"] == "pt"
    source = "local function soma(a, b) return a + b end"
    assert tokenizer.decode(tokenizer.encode(source)) == source


def test_generate_all_returns_seven_network_candidates_and_one_collective():
    model = HyperInterNetwork(**smoke_config()).eval()
    prefix = torch.tensor([[1, 80, 81, 82]])
    sequences = model.generate_all(prefix, max_new_tokens=3, temperature=0)
    assert len(sequences) == 8
    assert all(sequence.shape == (1, 7) for sequence in sequences)
}
