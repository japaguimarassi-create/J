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



def test_universal_foundation_weights_initialize_all_seven_networks():
    from foundation import UniversalFoundationModel, initialize_hyper_from_foundation

    config = smoke_config()
    foundation = UniversalFoundationModel(config)
    model = HyperInterNetwork(**config)
    payload = {
        "state_dict": foundation.state_dict(),
        "config": config,
        "tokenizer_sha256": "procedural-byte-v1",
        "in_progress": False,
    }
    initialize_hyper_from_foundation(
        model,
        payload,
        "procedural-byte-v1",
        config,
    )
    assert torch.equal(model.token_embedding.weight, foundation.token_embedding.weight)
    assert torch.equal(model.position_embedding, foundation.position_embedding)
    for index in range(7):
        for branch_block, base_block in zip(model.experts[index], foundation.blocks):
            assert torch.equal(
                branch_block.attention.qkv.weight,
                base_block.attention.qkv.weight,
            )
        assert torch.equal(model.expert_head_biases[index], foundation.output_bias)
        assert torch.equal(
            model.expert_norms[index].weight,
            foundation.norm.weight,
        )


def test_foundation_checkpoint_rejects_wrong_tokenizer_and_incomplete_state():
    import pytest
    from foundation import UniversalFoundationModel, initialize_hyper_from_foundation

    config = smoke_config()
    foundation = UniversalFoundationModel(config)
    model = HyperInterNetwork(**config)
    payload = {
        "state_dict": foundation.state_dict(),
        "config": config,
        "tokenizer_sha256": "expected",
        "in_progress": False,
    }
    with pytest.raises(ValueError):
        initialize_hyper_from_foundation(model, payload, "wrong", config)
    payload["tokenizer_sha256"] = "expected"
    payload["in_progress"] = True
    with pytest.raises(ValueError):
        initialize_hyper_from_foundation(model, payload, "expected", config)



def test_corpus_mixer_respects_weighted_quotas_and_preserves_provenance(tmp_path):
    import json
    from mix_corpus import mix_corpora

    sources = {}
    for name, count in (("code", 20), ("web", 20), ("math", 20), ("docs", 20)):
        path = tmp_path / f"{name}.jsonl"
        path.write_text(
            "".join(
                json.dumps({
                    "text": f"{name} unique sample {index}",
                    "repository": f"org/{name}-{index}",
                    "license": "MIT",
                    "language": "en",
                }) + "\n"
                for index in range(count)
            ),
            encoding="utf-8",
        )
        sources[name] = path

    output = tmp_path / "mixed.jsonl"
    report = mix_corpora(
        sources,
        {"code": 4, "web": 3, "math": 2, "docs": 1},
        output,
        max_records=20,
        seed=13,
    )
    records = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert report["records_written"] == 20
    assert report["source_counts"] == {"code": 8, "web": 6, "math": 4, "docs": 2}
    assert all(record["sha256"] and record["source"] in sources for record in records)
    assert all(record["license"] == "MIT" for record in records)


def test_corpus_mixer_exact_deduplication_and_license_filter(tmp_path):
    import json
    from mix_corpus import mix_corpora, parse_assignments
    import pytest

    code = tmp_path / "code.jsonl"
    web = tmp_path / "web.jsonl"
    code.write_text(
        json.dumps({"text": "same snippet", "license": "MIT"}) + "\n"
        + json.dumps({"text": "code only", "license": "MIT"}) + "\n",
        encoding="utf-8",
    )
    web.write_text(
        json.dumps({"text": "same snippet", "license": "MIT"}) + "\n"
        + json.dumps({"text": "no license"}) + "\n",
        encoding="utf-8",
    )
    output = tmp_path / "licensed.jsonl"
    report = mix_corpora(
        {"code": code, "web": web},
        {"code": 1, "web": 1},
        output,
        require_license=True,
    )
    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert report["records_written"] == 2
    assert sum(report["duplicates"].values()) == 1
    assert sum(report["missing_license"].values()) == 1
    assert len({row["sha256"] for row in rows}) == 2
    with pytest.raises(ValueError):
        parse_assignments(["../unsafe=/tmp/file.jsonl"], "source")
