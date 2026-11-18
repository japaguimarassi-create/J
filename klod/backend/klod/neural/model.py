from __future__ import annotations

from dataclasses import asdict, dataclass

import torch
from torch import nn
from torch.nn import functional as F


@dataclass(frozen=True)
class ModelConfig:
    vocab_size: int
    max_seq_len: int = 256
    d_model: int = 256
    n_heads: int = 4
    n_layers: int = 4
    d_ff: int = 1024
    rope_base: float = 10000.0

    def __post_init__(self) -> None:
        if self.vocab_size < 256 or self.d_model <= 0 or self.n_heads <= 0 or self.n_layers <= 0:
            raise ValueError("Invalid model dimensions")
        if self.d_model % self.n_heads or (self.d_model // self.n_heads) % 2:
            raise ValueError("d_model/head count must produce an even head dimension")
        if self.max_seq_len < 2 or self.d_ff < 1:
            raise ValueError("Invalid context or feed-forward dimension")

    def to_dict(self) -> dict[str, int | float]:
        return asdict(self)


class RMSNorm(nn.Module):
    def __init__(self, dimension: int, epsilon: float = 1e-6) -> None:
        super().__init__()
        self.weight = nn.Parameter(torch.ones(dimension))
        self.epsilon = epsilon

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        return value * torch.rsqrt(value.pow(2).mean(dim=-1, keepdim=True) + self.epsilon) * self.weight


def rotate_half(value: torch.Tensor) -> torch.Tensor:
    first, second = value.chunk(2, dim=-1)
    return torch.cat((-second, first), dim=-1)


class CausalSelfAttention(nn.Module):
    def __init__(self, config: ModelConfig) -> None:
        super().__init__()
        self.heads = config.n_heads
        self.head_dim = config.d_model // config.n_heads
        self.qkv = nn.Linear(config.d_model, config.d_model * 3, bias=False)
        self.projection = nn.Linear(config.d_model, config.d_model, bias=False)
        inverse = 1.0 / (config.rope_base ** (torch.arange(0, self.head_dim, 2).float() / self.head_dim))
        self.register_buffer("inverse_frequency", inverse, persistent=False)

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        batch, length, width = value.shape
        qkv = self.qkv(value).view(batch, length, 3, self.heads, self.head_dim)
        query, key, content = qkv.permute(2, 0, 3, 1, 4).unbind(0)
        positions = torch.arange(length, device=value.device, dtype=self.inverse_frequency.dtype)
        frequencies = torch.outer(positions, self.inverse_frequency)
        angles = torch.cat((frequencies, frequencies), dim=-1).to(query.dtype)
        cosine, sine = angles.cos()[None, None], angles.sin()[None, None]
        query = query * cosine + rotate_half(query) * sine
        key = key * cosine + rotate_half(key) * sine
        output = F.scaled_dot_product_attention(query, key, content, is_causal=True)
        output = output.transpose(1, 2).contiguous().view(batch, length, width)
        return self.projection(output)


class Block(nn.Module):
    def __init__(self, config: ModelConfig) -> None:
        super().__init__()
        self.norm1 = RMSNorm(config.d_model)
        self.attention = CausalSelfAttention(config)
        self.norm2 = RMSNorm(config.d_model)
        self.up = nn.Linear(config.d_model, config.d_ff)
        self.down = nn.Linear(config.d_ff, config.d_model)

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        value = value + self.attention(self.norm1(value))
        feed_forward = self.down(F.gelu(self.up(self.norm2(value)), approximate="tanh"))
        return value + feed_forward


class GPTModel(nn.Module):
    def __init__(self, config: ModelConfig) -> None:
        super().__init__()
        self.config = config
        self.embedding = nn.Embedding(config.vocab_size, config.d_model)
        self.blocks = nn.ModuleList([Block(config) for _ in range(config.n_layers)])
        self.final_norm = RMSNorm(config.d_model)
        self.output = nn.Linear(config.d_model, config.vocab_size, bias=False)
        self.output.weight = self.embedding.weight
        self.apply(self._initialize)

    @staticmethod
    def _initialize(module: nn.Module) -> None:
        if isinstance(module, (nn.Linear, nn.Embedding)):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if isinstance(module, nn.Linear) and module.bias is not None:
                nn.init.zeros_(module.bias)

    def parameter_count(self) -> int:
        return sum(parameter.numel() for parameter in self.parameters() if parameter.requires_grad)

    def forward(self, token_ids: torch.Tensor, targets: torch.Tensor | None = None):
        if token_ids.ndim != 2 or token_ids.shape[1] > self.config.max_seq_len:
            raise ValueError("Expected [batch, sequence] input within max_seq_len")
        value = self.embedding(token_ids)
        for block in self.blocks:
            value = block(value)
        logits = self.output(self.final_norm(value))
        loss = None
        if targets is not None:
            if targets.shape != token_ids.shape:
                raise ValueError("targets must match token_ids shape")
            loss = F.cross_entropy(logits[:, :-1].reshape(-1, logits.size(-1)), targets[:, 1:].reshape(-1))
        return logits, loss

    @torch.no_grad()
    def generate(self, token_ids: torch.Tensor, max_new_tokens: int = 64, temperature: float = 1.0, top_k: int | None = 40):
        if temperature <= 0 or max_new_tokens < 0:
            raise ValueError("Invalid generation settings")
        self.eval()
        generated = token_ids
        for _ in range(max_new_tokens):
            logits, _ = self(generated[:, -self.config.max_seq_len:])
            logits = logits[:, -1] / temperature
            if top_k is not None:
                count = min(max(1, top_k), logits.size(-1))
                cutoff = torch.topk(logits, count, dim=-1).values[:, -1, None]
                logits = logits.masked_fill(logits < cutoff, -torch.inf)
            next_token = torch.multinomial(F.softmax(logits, dim=-1), num_samples=1)
            generated = torch.cat((generated, next_token), dim=1)
        return generated
