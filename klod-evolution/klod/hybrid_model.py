from dataclasses import asdict, dataclass
from typing import Optional

import torch
from torch import nn
from torch.nn import functional as F


@dataclass
class HybridConfig:
    vocab_size: int = 258
    hidden_size: int = 40000
    logical_layers: int = 20000
    active_stages: int = 8
    attention_rank: int = 64
    attention_heads: int = 4
    dense_rank: int = 128
    expert_rank: int = 64
    stage_rank: int = 64
    n_experts: int = 8
    top_k_experts: int = 2
    max_seq_len: int = 256
    dropout: float = 0.05
    router_aux_weight: float = 0.01

    def validate(self) -> None:
        if self.vocab_size < 3:
            raise ValueError("vocab_size must be at least 3")
        if not 16 <= self.hidden_size <= 100000:
            raise ValueError("hidden_size must be between 16 and 100000")
        if not 1 <= self.logical_layers <= 100000:
            raise ValueError("logical_layers must be between 1 and 100000")
        if not 1 <= self.active_stages <= self.logical_layers:
            raise ValueError("active_stages must be between 1 and logical_layers")
        if not 8 <= self.attention_rank <= self.hidden_size:
            raise ValueError("attention_rank must be between 8 and hidden_size")
        if self.attention_heads < 1 or self.attention_rank % self.attention_heads:
            raise ValueError("attention_rank must be divisible by attention_heads")
        if not 1 <= self.dense_rank <= self.hidden_size:
            raise ValueError("dense_rank must be between 1 and hidden_size")
        if not 1 <= self.expert_rank <= self.hidden_size:
            raise ValueError("expert_rank must be between 1 and hidden_size")
        if not 1 <= self.stage_rank <= self.hidden_size:
            raise ValueError("stage_rank must be between 1 and hidden_size")
        if not 1 <= self.n_experts <= 64:
            raise ValueError("n_experts must be between 1 and 64")
        if not 1 <= self.top_k_experts <= self.n_experts:
            raise ValueError("top_k_experts must be between 1 and n_experts")
        if not 8 <= self.max_seq_len <= 8192:
            raise ValueError("max_seq_len must be between 8 and 8192")
        if not 0.0 <= self.dropout < 1.0:
            raise ValueError("dropout must be in [0, 1)")
        if self.router_aux_weight < 0:
            raise ValueError("router_aux_weight must be non-negative")


class FactorizedCausalAttention(nn.Module):
    def __init__(self, config: HybridConfig):
        super().__init__()
        hidden = config.hidden_size
        rank = config.attention_rank
        self.qkv_down = nn.Linear(hidden, rank * 3, bias=False)
        self.attention = nn.MultiheadAttention(
            rank,
            config.attention_heads,
            dropout=config.dropout,
            batch_first=True,
        )
        self.output_up = nn.Linear(rank, hidden, bias=False)
        self.dropout = nn.Dropout(config.dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        steps = x.size(1)
        q, k, v = self.qkv_down(x).chunk(3, dim=-1)
        mask = torch.triu(
            torch.ones(steps, steps, device=x.device, dtype=torch.bool),
            diagonal=1,
        )
        attended, _ = self.attention(
            q,
            k,
            v,
            attn_mask=mask,
            need_weights=False,
        )
        return self.dropout(self.output_up(attended))


class LowRankTransform(nn.Module):
    def __init__(self, hidden_size: int, rank: int, dropout: float):
        super().__init__()
        self.down = nn.Linear(hidden_size, rank, bias=False)
        self.activation = nn.GELU()
        self.dropout = nn.Dropout(dropout)
        self.up = nn.Linear(rank, hidden_size, bias=False)
        nn.init.zeros_(self.up.weight)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.up(self.dropout(self.activation(self.down(x))))


class SparseLowRankExperts(nn.Module):
    def __init__(self, config: HybridConfig):
        super().__init__()
        self.n_experts = config.n_experts
        self.top_k = config.top_k_experts
        self.router = nn.Linear(config.hidden_size, config.n_experts)
        self.experts = nn.ModuleList([
            LowRankTransform(
                config.hidden_size,
                config.expert_rank,
                config.dropout,
            )
            for _ in range(config.n_experts)
        ])

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        batch, steps, width = x.shape
        flat = x.reshape(-1, width)
        scores = self.router(flat)
        probabilities = scores.softmax(dim=-1)
        selected_values, selected_ids = torch.topk(
            scores,
            self.top_k,
            dim=-1,
        )
        selected_weights = selected_values.softmax(dim=-1)
        output = torch.zeros_like(flat)

        for expert_id, expert in enumerate(self.experts):
            positions = (selected_ids == expert_id).nonzero(as_tuple=False)
            if positions.numel() == 0:
                continue
            token_indices = positions[:, 0]
            slot_indices = positions[:, 1]
            expert_input = flat.index_select(0, token_indices)
            expert_output = expert(expert_input)
            weights = selected_weights[token_indices, slot_indices].unsqueeze(-1)
            output.index_add_(0, token_indices, expert_output * weights)

        load = F.one_hot(
            selected_ids,
            num_classes=self.n_experts,
        ).to(probabilities.dtype).mean(dim=(0, 1))
        importance = probabilities.mean(dim=0)
        auxiliary_loss = self.n_experts * torch.sum(importance * load)
        return output.view(batch, steps, width), auxiliary_loss


class SparseDepthRouter(nn.Module):
    def __init__(self, config: HybridConfig):
        super().__init__()
        self.logical_layers = config.logical_layers
        self.active_stages = config.active_stages
        self.down = nn.Linear(config.hidden_size, config.stage_rank, bias=False)
        self.up = nn.Linear(config.stage_rank, config.logical_layers)
        self.stage_embedding = nn.Embedding(config.logical_layers, config.stage_rank)
        self.stage_up = nn.Linear(config.stage_rank, config.hidden_size, bias=False)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        pooled = x.mean(dim=1)
        scores = self.up(F.gelu(self.down(pooled)))
        selected_scores, selected_ids = torch.topk(
            scores,
            self.active_stages,
            dim=-1,
        )
        selected_weights = selected_scores.softmax(dim=-1)
        probabilities = scores.softmax(dim=-1)
        load = F.one_hot(
            selected_ids,
            num_classes=self.logical_layers,
        ).to(probabilities.dtype).mean(dim=(0, 1))
        importance = probabilities.mean(dim=0)
        auxiliary_loss = self.logical_layers * torch.sum(importance * load)
        stage_vectors = self.stage_up(self.stage_embedding(selected_ids))
        return selected_ids, selected_weights, stage_vectors, auxiliary_loss


class HybridKlodModel(nn.Module):
    def __init__(self, config: Optional[HybridConfig] = None):
        super().__init__()
        self.config = config or HybridConfig()
        self.config.validate()
        hidden = self.config.hidden_size

        self.token_embedding = nn.Embedding(self.config.vocab_size, hidden)
        self.position_embedding = nn.Embedding(
            self.config.max_seq_len,
            self.config.stage_rank,
        )
        self.position_up = nn.Linear(self.config.stage_rank, hidden, bias=False)

        self.depth_router = SparseDepthRouter(self.config)
        self.attention_norm = nn.LayerNorm(hidden)
        self.shared_attention = FactorizedCausalAttention(self.config)

        self.dense_norm = nn.LayerNorm(hidden)
        self.shared_dense_core = LowRankTransform(
            hidden,
            self.config.dense_rank,
            self.config.dropout,
        )

        self.expert_norm = nn.LayerNorm(hidden)
        self.sparse_experts = SparseLowRankExperts(self.config)
        self.sparse_gate = nn.Linear(hidden, 1)
        nn.init.constant_(self.sparse_gate.bias, -1.0)

        self.final_norm = nn.LayerNorm(hidden)
        self.lm_down = nn.Linear(hidden, self.config.attention_rank, bias=False)
        self.lm_head = nn.Linear(
            self.config.attention_rank,
            self.config.vocab_size,
            bias=False,
        )
        self.dropout = nn.Dropout(self.config.dropout)

    def forward(
        self,
        input_ids: torch.Tensor,
        targets: Optional[torch.Tensor] = None,
    ) -> tuple[torch.Tensor, Optional[torch.Tensor]]:
        if input_ids.ndim != 2:
            raise ValueError("input_ids must have shape [batch, sequence]")
        if input_ids.size(1) > self.config.max_seq_len:
            raise ValueError("sequence exceeds max_seq_len")

        batch, steps = input_ids.shape
        positions = torch.arange(steps, device=input_ids.device)
        position_vectors = self.position_up(self.position_embedding(positions))
        x = self.token_embedding(input_ids) + position_vectors.unsqueeze(0)
        x = self.dropout(x)

        _, stage_weights, stage_vectors, stage_aux = self.depth_router(x)
        expert_auxiliary_losses = []

        for stage_slot in range(self.config.active_stages):
            stage_weight = stage_weights[:, stage_slot].view(batch, 1, 1)
            stage_vector = stage_vectors[:, stage_slot, :].unsqueeze(1)
            conditioned = x + stage_vector

            attention_delta = self.shared_attention(
                self.attention_norm(conditioned)
            )
            x = x + stage_weight * attention_delta

            dense_delta = self.shared_dense_core(self.dense_norm(x))
            expert_input = self.expert_norm(x)
            sparse_delta, expert_aux = self.sparse_experts(expert_input)
            gate = torch.sigmoid(self.sparse_gate(expert_input))
            x = x + stage_weight * (
                dense_delta + gate * sparse_delta
            )
            expert_auxiliary_losses.append(expert_aux)

        logits = self.lm_head(self.lm_down(self.final_norm(x)))
        loss = None
        if targets is not None:
            if targets.shape != input_ids.shape:
                raise ValueError("targets must have the same shape as input_ids")
            language_loss = F.cross_entropy(
                logits.reshape(-1, self.config.vocab_size),
                targets.reshape(-1),
            )
            expert_aux = torch.stack(expert_auxiliary_losses).mean()
            loss = language_loss + self.config.router_aux_weight * (
                stage_aux + expert_aux
            )
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
                cutoff = torch.topk(
                    next_logits,
                    top_k,
                    dim=-1,
                ).values[:, -1, None]
                next_logits = next_logits.masked_fill(
                    next_logits < cutoff,
                    float("-inf"),
                )
            next_token = torch.multinomial(
                next_logits.softmax(dim=-1),
                num_samples=1,
            )
            result = torch.cat((result, next_token), dim=1)
            if bool((next_token == 1).all()):
                break
        return result

    def export_config(self) -> dict:
        return asdict(self.config)

    def parameter_count(self) -> int:
        return sum(parameter.numel() for parameter in self.parameters())
