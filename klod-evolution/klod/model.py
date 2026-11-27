from dataclasses import asdict, dataclass
from typing import Optional

import torch
from torch import nn
from torch.nn import functional as F


@dataclass
class ModelConfig:
    vocab_size: int = 258
    d_model: int = 128
    n_heads: int = 4
    n_layers: int = 6
    n_experts: int = 4
    max_seq_len: int = 256
    dropout: float = 0.05

    def validate(self) -> None:
        if self.vocab_size < 3:
            raise ValueError("vocab_size must be at least 3")
        if self.d_model < 16 or self.d_model > 2048:
            raise ValueError("d_model must be between 16 and 2048")
        if self.n_heads < 1 or self.d_model % self.n_heads:
            raise ValueError("d_model must be divisible by n_heads")
        if not 1 <= self.n_layers <= 64:
            raise ValueError("n_layers must be between 1 and 64")
        if not 1 <= self.n_experts <= 16:
            raise ValueError("n_experts must be between 1 and 16")
        if not 8 <= self.max_seq_len <= 8192:
            raise ValueError("max_seq_len must be between 8 and 8192")
        if not 0.0 <= self.dropout < 1.0:
            raise ValueError("dropout must be in [0, 1)")


class ByteTokenizer:
    pad_id = 0
    eos_id = 1
    offset = 2
    vocab_size = 258

    def encode(self, text: str, add_eos: bool = True) -> list[int]:
        ids = [value + self.offset for value in text.encode("utf-8")]
        if add_eos:
            ids.append(self.eos_id)
        return ids

    def decode(self, ids: list[int]) -> str:
        data = bytearray()
        for token in ids:
            if token == self.eos_id:
                break
            if token >= self.offset:
                data.append(token - self.offset)
        return data.decode("utf-8", errors="replace")


class SparseMoE(nn.Module):
    def __init__(self, config: ModelConfig):
        super().__init__()
        self.router = nn.Linear(config.d_model, config.n_experts)
        self.experts = nn.ModuleList([
            nn.Sequential(
                nn.Linear(config.d_model, config.d_model * 4),
                nn.GELU(),
                nn.Linear(config.d_model * 4, config.d_model),
            )
            for _ in range(config.n_experts)
        ])

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        batch, steps, width = x.shape
        flat = x.reshape(-1, width)
        scores = self.router(flat)
        selected_ids = scores.argmax(dim=-1)
        weights = scores.softmax(dim=-1).gather(1, selected_ids.unsqueeze(1))
        output = torch.zeros_like(flat)
        for expert_id, expert in enumerate(self.experts):
            indices = (selected_ids == expert_id).nonzero(as_tuple=False).flatten()
            if indices.numel() == 0:
                continue
            values = expert(flat.index_select(0, indices))
            output.index_copy_(0, indices, values * weights.index_select(0, indices))
        return output.view(batch, steps, width)


class DecoderBlock(nn.Module):
    def __init__(self, config: ModelConfig):
        super().__init__()
        self.norm1 = nn.LayerNorm(config.d_model)
        self.attention = nn.MultiheadAttention(
            config.d_model,
            config.n_heads,
            dropout=config.dropout,
            batch_first=True,
        )
        self.norm2 = nn.LayerNorm(config.d_model)
        self.moe = SparseMoE(config)
        self.dropout = nn.Dropout(config.dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        steps = x.size(1)
        mask = torch.triu(
            torch.ones(steps, steps, device=x.device, dtype=torch.bool),
            diagonal=1,
        )
        normalized = self.norm1(x)
        attended, _ = self.attention(
            normalized,
            normalized,
            normalized,
            attn_mask=mask,
            need_weights=False,
        )
        x = x + self.dropout(attended)
        x = x + self.dropout(self.moe(self.norm2(x)))
        return x


class KlodModel(nn.Module):
    def __init__(self, config: Optional[ModelConfig] = None):
        super().__init__()
        self.config = config or ModelConfig()
        self.config.validate()
        self.token_embedding = nn.Embedding(self.config.vocab_size, self.config.d_model)
        self.position_embedding = nn.Embedding(self.config.max_seq_len, self.config.d_model)
        self.blocks = nn.ModuleList([DecoderBlock(self.config) for _ in range(self.config.n_layers)])
        self.final_norm = nn.LayerNorm(self.config.d_model)
        self.output = nn.Linear(self.config.d_model, self.config.vocab_size, bias=False)
        self.output.weight = self.token_embedding.weight

    def forward(
        self,
        input_ids: torch.Tensor,
        targets: Optional[torch.Tensor] = None,
    ) -> tuple[torch.Tensor, Optional[torch.Tensor]]:
        if input_ids.ndim != 2:
            raise ValueError("input_ids must have shape [batch, sequence]")
        if input_ids.size(1) > self.config.max_seq_len:
            raise ValueError("sequence exceeds max_seq_len")
        positions = torch.arange(input_ids.size(1), device=input_ids.device)
        x = self.token_embedding(input_ids) + self.position_embedding(positions)[None, :, :]
        for block in self.blocks:
            x = block(x)
        logits = self.output(self.final_norm(x))
        loss = None
        if targets is not None:
            loss = F.cross_entropy(logits.reshape(-1, self.config.vocab_size), targets.reshape(-1))
        return logits, loss

    @torch.inference_mode()
    def generate(
        self,
        input_ids: torch.Tensor,
        max_new_tokens: int = 160,
        temperature: float = 0.8,
        top_k: int = 40,
    ) -> torch.Tensor:
        if max_new_tokens < 1 or max_new_tokens > 2048:
            raise ValueError("max_new_tokens must be between 1 and 2048")
        if temperature <= 0:
            raise ValueError("temperature must be positive")
        self.eval()
        result = input_ids
        for _ in range(max_new_tokens):
            context = result[:, -self.config.max_seq_len:]
            logits, _ = self(context)
            next_logits = logits[:, -1, :] / temperature
            if 0 < top_k < next_logits.size(-1):
                cutoff = torch.topk(next_logits, top_k, dim=-1).values[:, -1, None]
                next_logits = next_logits.masked_fill(next_logits < cutoff, float("-inf"))
            next_token = torch.multinomial(next_logits.softmax(dim=-1), num_samples=1)
            result = torch.cat((result, next_token), dim=1)
            if bool((next_token == ByteTokenizer.eos_id).all()):
                break
        return result

    def export_config(self) -> dict:
        return asdict(self.config)
