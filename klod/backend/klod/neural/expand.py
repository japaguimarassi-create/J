from __future__ import annotations

from dataclasses import dataclass

import torch

from .model import GPTModel, ModelConfig


@dataclass(frozen=True)
class ExpansionReport:
    previous_parameters: int
    expanded_parameters: int
    copied_parameter_elements: int
    added_layers: int
    added_feed_forward_width: int
    added_vocabulary_items: int


def expand_model(source: GPTModel, target_config: ModelConfig) -> tuple[GPTModel, ExpansionReport]:
    previous = source.config
    if target_config.d_model != previous.d_model:
        raise ValueError("Width changes require a separately validated architecture migration")
    if target_config.n_heads != previous.n_heads:
        raise ValueError("Head-count changes require a separately validated architecture migration")
    if target_config.n_layers < previous.n_layers:
        raise ValueError("Model expansion cannot remove Transformer layers")
    if target_config.d_ff < previous.d_ff:
        raise ValueError("Model expansion cannot shrink the feed-forward width")
    if target_config.vocab_size < previous.vocab_size:
        raise ValueError("Model expansion cannot shrink the vocabulary")
    if target_config.max_seq_len < previous.max_seq_len:
        raise ValueError("Model expansion cannot shrink the context window")

    expanded = GPTModel(target_config)
    source_state = source.state_dict()
    target_state = expanded.state_dict()
    copied_elements = 0

    for name, old_tensor in source_state.items():
        if name not in target_state:
            raise ValueError(f"Target architecture is missing parameter: {name}")
        new_tensor = target_state[name]
        if old_tensor.ndim != new_tensor.ndim:
            raise ValueError(f"Parameter rank changed during expansion: {name}")
        if old_tensor.shape == new_tensor.shape:
            new_tensor.copy_(old_tensor)
            copied_elements += old_tensor.numel()
            continue

        if name in {"embedding.weight", "output.weight"}:
            rows = min(old_tensor.shape[0], new_tensor.shape[0])
            new_tensor[:rows].copy_(old_tensor[:rows])
            if new_tensor.shape[0] > rows:
                new_tensor[rows:].zero_()
            copied_elements += old_tensor.numel()
        elif name.endswith(".up.weight"):
            rows = old_tensor.shape[0]
            new_tensor[:rows].copy_(old_tensor)
            copied_elements += old_tensor.numel()
        elif name.endswith(".up.bias"):
            new_tensor[:old_tensor.shape[0]].copy_(old_tensor)
            copied_elements += old_tensor.numel()
        elif name.endswith(".down.weight"):
            columns = old_tensor.shape[1]
            new_tensor[:, :columns].copy_(old_tensor)
            if new_tensor.shape[1] > columns:
                new_tensor[:, columns:].zero_()
            copied_elements += old_tensor.numel()
        else:
            raise ValueError(f"Unsupported parameter shape change: {name} {tuple(old_tensor.shape)} -> {tuple(new_tensor.shape)}")

    expanded.load_state_dict(target_state, strict=True)
    with torch.no_grad():
        for index in range(previous.n_layers, target_config.n_layers):
            block = expanded.blocks[index]
            block.attention.projection.weight.zero_()
            block.down.weight.zero_()

    report = ExpansionReport(
        previous_parameters=source.parameter_count(),
        expanded_parameters=expanded.parameter_count(),
        copied_parameter_elements=copied_elements,
        added_layers=target_config.n_layers - previous.n_layers,
        added_feed_forward_width=target_config.d_ff - previous.d_ff,
        added_vocabulary_items=target_config.vocab_size - previous.vocab_size,
    )
    return expanded, report
