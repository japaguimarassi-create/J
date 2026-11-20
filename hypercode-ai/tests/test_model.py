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
    assert config["vocab_size"] == 32768
    assert config["context_length"] == 2048
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
    assert len(model.expert_head_biases) == 7
    assert not hasattr(model, "expert_heads")


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


def test_sft_masks_user_prompt_and_trains_only_assistant_completion(tmp_path):
    import json
    from finetune import load_instruction_chunks, make_batch

    prompt = "<|user|>Crie uma função soma.<|assistant|>\n"
    completion = "def soma(a, b):\n    return a + b\n"
    data = tmp_path / "instructions.jsonl"
    data.write_text(
        "".join(
            json.dumps({
                "prompt": prompt,
                "completion": completion,
                "language": "pt",
                "kind": "code",
            }) + "\n"
            for _ in range(5)
        ),
        encoding="utf-8",
    )
    tokenizer = ProceduralTokenizer()
    train_samples, validation_samples = load_instruction_chunks(data, tokenizer, 128, seed=7)
    assert train_samples and validation_samples
    inputs, targets = make_batch(train_samples, 1, 128, torch.device("cpu"))
    answer_start = len(prompt.encode("utf-8"))
    assert torch.all(targets[0, :answer_start] == -100)
    assert targets[0, answer_start] != -100
    assert inputs.shape == (1, 128)


def test_stack_v13_license_and_language_fields():
    from prepare_stack import license_values, TARGET_LANGUAGES, scan_secrets

    assert license_values('["MIT", "Apache-2.0"]') == ["apache-2.0", "mit"]
    assert license_values("MIT") == ["mit"]
    assert TARGET_LANGUAGES["c-sharp"] == "csharp"
    assert TARGET_LANGUAGES["rust"] == "rust"
    assert scan_secrets("ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890")
    assert not scan_secrets("def add(a, b): return a + b")


def test_pretraining_split_keeps_repository_groups_together():
    from train import split_by_repository

    records = [
        ("org/repo-a", [1, 4, 5, 2]),
        ("org/repo-a", [1, 6, 7, 2]),
        ("org/repo-b", [1, 8, 9, 2]),
        ("org/repo-c", [1, 10, 11, 2]),
    ]
    train_docs, validation_docs = split_by_repository(records, seed=1)
    train_tokens = {tuple(document) for document in train_docs}
    validation_tokens = {tuple(document) for document in validation_docs}
    assert train_tokens.isdisjoint(validation_tokens)
    assert len(train_docs) + len(validation_docs) == len(records)



def test_individual_expert_and_independent_core_bypass_communication():
    model = HyperInterNetwork(**smoke_config()).eval()
    calls = [0] * 2
    handles = [
        model.communication[0].register_forward_hook(lambda *args: calls.__setitem__(0, calls[0] + 1)),
        model.communication[1].register_forward_hook(lambda *args: calls.__setitem__(1, calls[1] + 1)),
    ]
    tokens = torch.randint(4, 260, (1, 16))
    expert_logits = model.forward_expert(tokens, 3)
    core_logits = model(tokens, use_communication=False)
    for handle in handles:
        handle.remove()
    assert expert_logits.shape == (1, 16, 260)
    assert core_logits.shape == (1, 16, 260)
    assert calls == [0, 0]


def test_staged_training_freezes_unselected_components():
    from staged_train import configure_stage

    model = HyperInterNetwork(**smoke_config())
    configure_stage(model, "expert", 4)
    assert not model.token_embedding.weight.requires_grad
    assert not model.position_embedding.requires_grad
    assert model.expert_head_biases[4].requires_grad
    assert any(parameter.requires_grad for parameter in model.experts[4].parameters())
    assert all(not parameter.requires_grad for parameter in model.experts[3].parameters())
    assert all(not parameter.requires_grad for parameter in model.communication.parameters())
    assert all(not parameter.requires_grad for parameter in model.fusion_blocks.parameters())

    configure_stage(model, "expert", 0)
    assert model.token_embedding.weight.requires_grad
    assert model.position_embedding.requires_grad
    assert model.expert_head_biases[0].requires_grad

    configure_stage(model, "core")
    assert all(parameter.requires_grad for parameter in model.fusion_blocks.parameters())
    assert all(not parameter.requires_grad for parameter in model.communication.parameters())
    assert all(not parameter.requires_grad for parameter in model.experts.parameters())

    configure_stage(model, "communication")
    assert all(parameter.requires_grad for parameter in model.communication.parameters())
    assert all(not parameter.requires_grad for parameter in model.experts.parameters())
    assert all(not parameter.requires_grad for parameter in model.fusion_blocks.parameters())

    configure_stage(model, "joint")
    assert all(parameter.requires_grad for parameter in model.parameters())


def test_stage_order_requires_seven_networks_then_core_then_communication():
    import pytest
    from staged_train import validate_stage_prerequisites

    with pytest.raises(ValueError):
        validate_stage_prerequisites("core", None, {0, 1, 2}, set())
    with pytest.raises(ValueError):
        validate_stage_prerequisites("communication", None, set(range(7)), set())
    with pytest.raises(ValueError):
        validate_stage_prerequisites("joint", None, set(range(7)), {"core"})
    validate_stage_prerequisites("core", None, set(range(7)), set())
    validate_stage_prerequisites("communication", None, set(range(7)), {"core"})
    validate_stage_prerequisites("joint", None, set(range(7)), {"core", "communication"})



def test_validation_gate_rejects_regression_and_accepts_improvement():
    from staged_train import validation_gate_passes

    assert validation_gate_passes(3.0, 2.9)
    assert validation_gate_passes(3.0, 3.0)
    assert validation_gate_passes(3.0, 3.0005, tolerance=0.001)
    assert not validation_gate_passes(3.0, 3.01)
    assert not validation_gate_passes(3.0, float("nan"))



def test_wsd_scheduler_warmup_stable_and_linear_decay():
    from optimization import wsd_multiplier

    assert wsd_multiplier(1, 100, 10, 0.1) == 0.1
    assert wsd_multiplier(10, 100, 10, 0.1) == 1.0
    assert wsd_multiplier(50, 100, 10, 0.1) == 1.0
    assert 0.0 < wsd_multiplier(95, 100, 10, 0.1) < 1.0
    assert wsd_multiplier(100, 100, 10, 0.1) == 0.0
    assert wsd_multiplier(1, 1, 2000, 0.1) == 1.0


def test_bpe_tokenizer_training_round_trip(tmp_path):
    import json
    from train_bpe_tokenizer import train_bpe
    from tokenizer import load_tokenizer

    corpus = tmp_path / "corpus.jsonl"
    samples = [
        "def soma(a, b): return a + b\n",
        "local function soma(a, b) return a + b end\n",
        "Crie uma função para somar dois números.\n",
        "The model learns code and natural language together.\n",
    ]
    corpus.write_text(
        "".join(json.dumps({"text": sample}) + "\n" for sample in samples * 8),
        encoding="utf-8",
    )
    destination = tmp_path / "tokenizer.json"
    report = train_bpe(corpus, destination, vocab_size=320, min_frequency=1)
    tokenizer = load_tokenizer(destination)
    source = "local function soma(a, b) return a + b end"
    assert report["actual_vocab_size"] == tokenizer.vocab_size
    assert tokenizer.encode(source)[0] == 1
    assert tokenizer.encode(source)[-1] == 2
    assert tokenizer.decode(tokenizer.encode(source)) == source


def test_sft_masks_prompt_using_bpe_character_offsets(tmp_path):
    import json
    from finetune import load_instruction_chunks, make_batch
    from train_bpe_tokenizer import train_bpe
    from tokenizer import load_tokenizer

    prompt = "<|user|>Crie uma função soma.<|assistant|>\n"
    completion = "def soma(a, b):\n    return a + b\n"
    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text(
        "".join(json.dumps({"text": prompt + completion}) + "\n" for _ in range(8)),
        encoding="utf-8",
    )
    tokenizer_path = tmp_path / "tokenizer.json"
    train_bpe(corpus, tokenizer_path, vocab_size=320, min_frequency=1)
    tokenizer = load_tokenizer(tokenizer_path)
    data = tmp_path / "instructions.jsonl"
    data.write_text(
        "".join(json.dumps({"prompt": prompt, "completion": completion}) + "\n" for _ in range(8)),
        encoding="utf-8",
    )
    train_samples, validation_samples = load_instruction_chunks(
        data, tokenizer, 128, seed=7
    )
    assert train_samples and validation_samples
    inputs, targets = make_batch(train_samples, 1, 128, torch.device("cpu"))
    assert torch.any(targets[0] == -100)
    first_unmasked = int(torch.where(targets[0] != -100)[0][0].item())
    assert first_unmasked < 128
    assert inputs.shape == (1, 128)


def test_weight_tying_uses_shared_vocabulary_projection():
    model = HyperInterNetwork(**smoke_config())
    states = torch.randn(2, 7, 5, 32)
    logits = model.forward_from_expert_states(states)
    assert logits.shape == (2, 5, 260)
    assert len(model.expert_head_biases) == 7
    assert not hasattr(model, "expert_heads")
