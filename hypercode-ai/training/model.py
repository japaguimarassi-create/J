import torch
from torch import nn
from torch.nn import functional as F


class CausalBlock(nn.Module):
    def __init__(self, width, heads, feed_forward, dropout=0.0):
        super().__init__()
        self.norm_attention = nn.LayerNorm(width)
        self.attention = nn.MultiheadAttention(width, heads, dropout=dropout, batch_first=True)
        self.norm_mlp = nn.LayerNorm(width)
        self.mlp = nn.Sequential(
            nn.Linear(width, feed_forward),
            nn.GELU(),
            nn.Linear(feed_forward, width),
            nn.Dropout(dropout),
        )

    def forward(self, value, causal_mask):
        normalized = self.norm_attention(value)
        attended, _ = self.attention(normalized, normalized, normalized, attn_mask=causal_mask, need_weights=False)
        value = value + attended
        return value + self.mlp(self.norm_mlp(value))


class CausalStack(nn.Module):
    def __init__(self, width, depth, heads, feed_forward, dropout=0.0):
        super().__init__()
        self.blocks = nn.ModuleList([
            CausalBlock(width, heads, feed_forward, dropout)
            for _ in range(depth)
        ])
        self.final_norm = nn.LayerNorm(width)

    def forward(self, value, causal_mask):
        for block in self.blocks:
            value = block(value, causal_mask)
        return self.final_norm(value)


class HyperInterNetwork(nn.Module):
    def __init__(
        self,
        vocab_size=260,
        context_length=256,
        experts=7,
        expert_layers=10,
        expert_width=256,
        expert_heads=8,
        expert_ff=768,
        fusion_layers=20,
        fusion_width=1792,
        fusion_heads=16,
        fusion_ff=2048,
        dropout=0.0,
    ):
        super().__init__()
        if experts != 7:
            raise ValueError("The target architecture requires exactly seven expert networks.")
        if fusion_width != experts * expert_width:
            raise ValueError("Fusion width must equal the concatenated width of all seven experts.")
        if expert_width % expert_heads != 0 or fusion_width % fusion_heads != 0:
            raise ValueError("Attention widths must be divisible by their head counts.")

        self.vocab_size = vocab_size
        self.context_length = context_length
        self.token_embedding = nn.Embedding(vocab_size, expert_width)
        self.expert_positions = nn.Parameter(torch.zeros(1, context_length, expert_width))
        self.experts = nn.ModuleList([
            CausalStack(expert_width, expert_layers, expert_heads, expert_ff, dropout)
            for _ in range(experts)
        ])
        self.fusion_positions = nn.Parameter(torch.zeros(1, context_length, fusion_width))
        self.fusion = CausalStack(fusion_width, fusion_layers, fusion_heads, fusion_ff, dropout)
        self.output_projection = nn.Linear(fusion_width, expert_width, bias=False)
        self.output_norm = nn.LayerNorm(expert_width)
        self.output_bias = nn.Parameter(torch.zeros(vocab_size))
        nn.init.normal_(self.expert_positions, mean=0.0, std=0.02)
        nn.init.normal_(self.fusion_positions, mean=0.0, std=0.02)

    def forward(self, input_ids, expert_id=0):
        _, sequence = input_ids.shape
        if sequence > self.context_length:
            raise ValueError("Input sequence exceeds configured context length.")
        if expert_id < 0 or expert_id >= len(self.experts):
            raise ValueError("expert_id must be between 0 and 6.")

        causal_mask = torch.triu(
            torch.ones(sequence, sequence, device=input_ids.device, dtype=torch.bool),
            diagonal=1,
        )
        embedded = self.token_embedding(input_ids) + self.expert_positions[:, :sequence]
        selected = self.experts[expert_id](embedded, causal_mask)
        inactive = torch.zeros_like(selected)
        routed = [selected if index == expert_id else inactive for index in range(7)]
        fused = torch.cat(routed, dim=-1) + self.fusion_positions[:, :sequence]
        hidden = self.fusion(fused, causal_mask)
        hidden = self.output_norm(self.output_projection(hidden))
        return F.linear(hidden, self.token_embedding.weight, self.output_bias)


def target_config():
    return {
        "vocab_size": 260,
        "context_length": 256,
        "experts": 7,
        "expert_layers": 10,
        "expert_width": 256,
        "expert_heads": 8,
        "expert_ff": 768,
        "fusion_layers": 20,
        "fusion_width": 1792,
        "fusion_heads": 16,
        "fusion_ff": 2048,
        "dropout": 0.0,
    }


def smoke_config():
    return {
        "vocab_size": 260,
        "context_length": 64,
        "experts": 7,
        "expert_layers": 1,
        "expert_width": 32,
        "expert_heads": 4,
        "expert_ff": 64,
        "fusion_layers": 2,
        "fusion_width": 224,
        "fusion_heads": 7,
        "fusion_ff": 256,
        "dropout": 0.0,
    }
