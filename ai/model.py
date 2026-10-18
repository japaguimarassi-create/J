import math

import torch
from torch import nn
from torch.nn import functional as F
from torch.utils.checkpoint import checkpoint

from ai.config import ModelConfig


class RMSNorm(nn.Module):
    def __init__(self, width, eps):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(width))
        self.eps = eps

    def forward(self, value):
        result = value.float() * torch.rsqrt(value.float().pow(2).mean(dim=-1, keepdim=True) + self.eps)
        return result.to(value.dtype) * self.weight.to(value.dtype)


def rotate_half(value):
    left, right = value.chunk(2, dim=-1)
    return torch.cat((-right, left), dim=-1)


def apply_rope(query, key, theta):
    length = query.shape[-2]
    width = query.shape[-1]
    inverse = 1.0 / (theta ** (torch.arange(0, width, 2, device=query.device, dtype=torch.float32) / width))
    positions = torch.arange(length, device=query.device, dtype=torch.float32)
    angles = torch.outer(positions, inverse)
    angles = torch.cat((angles, angles), dim=-1)
    cosine = angles.cos().to(query.dtype)[None, None, :, :]
    sine = angles.sin().to(query.dtype)[None, None, :, :]
    return (
        query * cosine + rotate_half(query) * sine,
        key * cosine + rotate_half(key) * sine,
    )


class GroupedQueryAttention(nn.Module):
    def __init__(self, config):
        super().__init__()
        hidden = config.hidden_size
        self.heads = config.num_attention_heads
        self.kv_heads = config.num_key_value_heads
        self.head_dim = hidden // self.heads
        self.kv_width = self.kv_heads * self.head_dim
        self.theta = config.rope_theta
        self.q_proj = nn.Linear(hidden, hidden, bias=False)
        self.k_proj = nn.Linear(hidden, self.kv_width, bias=False)
        self.v_proj = nn.Linear(hidden, self.kv_width, bias=False)
        self.o_proj = nn.Linear(hidden, hidden, bias=False)

    def forward(self, value):
        batch, length, hidden = value.shape
        query = self.q_proj(value).view(batch, length, self.heads, self.head_dim).transpose(1, 2)
        key = self.k_proj(value).view(batch, length, self.kv_heads, self.head_dim).transpose(1, 2)
        content = self.v_proj(value).view(batch, length, self.kv_heads, self.head_dim).transpose(1, 2)
        query, key = apply_rope(query, key, self.theta)
        if self.kv_heads != self.heads:
            repeat = self.heads // self.kv_heads
            key = key.repeat_interleave(repeat, dim=1)
            content = content.repeat_interleave(repeat, dim=1)
        attended = F.scaled_dot_product_attention(query, key, content, is_causal=True)
        attended = attended.transpose(1, 2).contiguous().view(batch, length, hidden)
        return self.o_proj(attended)


class SwiGLU(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.gate_proj = nn.Linear(config.hidden_size, config.intermediate_size, bias=False)
        self.up_proj = nn.Linear(config.hidden_size, config.intermediate_size, bias=False)
        self.down_proj = nn.Linear(config.intermediate_size, config.hidden_size, bias=False)

    def forward(self, value):
        return self.down_proj(F.silu(self.gate_proj(value)) * self.up_proj(value))


class TransformerBlock(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.input_norm = RMSNorm(config.hidden_size, config.rms_norm_eps)
        self.attention = GroupedQueryAttention(config)
        self.post_attention_norm = RMSNorm(config.hidden_size, config.rms_norm_eps)
        self.mlp = SwiGLU(config)

    def forward(self, value):
        value = value + self.attention(self.input_norm(value))
        return value + self.mlp(self.post_attention_norm(value))


class KoworkLM(nn.Module):
    def __init__(self, config=None, device=None):
        super().__init__()
        self.config = config or ModelConfig()
        self.config.validate()
        device_context = torch.device(device) if device is not None else torch.device("cpu")
        with device_context:
            self.embed_tokens = nn.Embedding(self.config.vocab_size, self.config.hidden_size)
            self.layers = nn.ModuleList(TransformerBlock(self.config) for _ in range(self.config.num_layers))
            self.final_norm = RMSNorm(self.config.hidden_size, self.config.rms_norm_eps)
            self.lm_head = nn.Linear(self.config.hidden_size, self.config.vocab_size, bias=False)
        self.apply(self._initialize)

    def _initialize(self, module):
        if isinstance(module, (nn.Linear, nn.Embedding)):
            std = 0.02
            if isinstance(module, nn.Linear) and module.out_features == self.config.hidden_size:
                if module.in_features == self.config.intermediate_size or module.in_features == self.config.hidden_size:
                    std /= math.sqrt(2 * self.config.num_layers)
            nn.init.normal_(module.weight, mean=0.0, std=std)
            if isinstance(module, nn.Linear) and module.bias is not None:
                nn.init.zeros_(module.bias)

    def forward(self, input_ids):
        if input_ids.ndim != 2:
            raise ValueError("input_ids must have shape [batch, sequence]")
        length = input_ids.shape[1]
        if length < 1 or length > self.config.max_seq_len:
            raise ValueError("Input sequence length is outside the configured range")
        value = self.embed_tokens(input_ids)
        for layer in self.layers:
            if self.config.gradient_checkpointing and self.training and value.requires_grad:
                value = checkpoint(layer, value, use_reentrant=False)
            else:
                value = layer(value)
        return self.lm_head(self.final_norm(value))

    @torch.inference_mode()
    def generate(self, input_ids, max_new_tokens=160, eos_token_id=None, temperature=0.8, top_k=40):
        if input_ids.ndim != 2 or input_ids.shape[0] != 1 or input_ids.shape[1] < 1:
            raise ValueError("Generation expects a non-empty prompt with batch size 1")
        if temperature <= 0:
            raise ValueError("temperature must be positive")
        self.eval()
        for _ in range(max(0, min(int(max_new_tokens), 2048))):
            context = input_ids[:, -self.config.max_seq_len:]
            logits = self(context)[:, -1, :] / temperature
            if top_k > 0:
                k = min(int(top_k), logits.shape[-1])
                cutoff = torch.topk(logits, k, dim=-1).values[:, -1, None]
                logits = logits.masked_fill(logits < cutoff, float("-inf"))
            next_token = torch.multinomial(torch.softmax(logits, dim=-1), num_samples=1)
            input_ids = torch.cat((input_ids, next_token), dim=1)
            if eos_token_id is not None and int(next_token.item()) == eos_token_id:
                break
        return input_ids
