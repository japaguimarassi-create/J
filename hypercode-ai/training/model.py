import torch
from torch import nn
from torch.nn import functional as F
from torch.utils.checkpoint import checkpoint


class CausalSelfAttention(nn.Module):
    def __init__(self, width, heads, dropout=0.0):
        super().__init__()
        if width % heads:
            raise ValueError("Attention width must be divisible by head count.")
        self.heads = heads
        self.head_width = width // heads
        self.dropout = dropout
        self.qkv = nn.Linear(width, width * 3, bias=False)
        self.output = nn.Linear(width, width, bias=False)

    def forward(self, value):
        batch, sequence, width = value.shape
        q, k, v = self.qkv(value).view(
            batch, sequence, 3, self.heads, self.head_width
        ).permute(2, 0, 3, 1, 4).unbind(0)
        attended = F.scaled_dot_product_attention(
            q,
            k,
            v,
            dropout_p=self.dropout if self.training else 0.0,
            is_causal=True,
        )
        attended = attended.transpose(1, 2).contiguous().view(batch, sequence, width)
        return self.output(attended)


class CausalBlock(nn.Module):
    def __init__(self, width, heads, feed_forward, dropout=0.0):
        super().__init__()
        self.norm_attention = nn.LayerNorm(width)
        self.attention = CausalSelfAttention(width, heads, dropout)
        self.norm_mlp = nn.LayerNorm(width)
        self.mlp = nn.Sequential(
            nn.Linear(width, feed_forward),
            nn.GELU(),
            nn.Linear(feed_forward, width),
            nn.Dropout(dropout),
        )

    def forward(self, value):
        value = value + self.attention(self.norm_attention(value))
        return value + self.mlp(self.norm_mlp(value))


class MutualCommunication(nn.Module):
    def __init__(self, width, heads, feed_forward, dropout=0.0):
        super().__init__()
        if width % heads:
            raise ValueError("Communication width must be divisible by head count.")
        self.heads = heads
        self.head_width = width // heads
        self.dropout = dropout
        self.norm_attention = nn.LayerNorm(width)
        self.qkv = nn.Linear(width, width * 3, bias=False)
        self.output = nn.Linear(width, width, bias=False)
        self.norm_mlp = nn.LayerNorm(width)
        self.mlp = nn.Sequential(
            nn.Linear(width, feed_forward),
            nn.GELU(),
            nn.Linear(feed_forward, width),
            nn.Dropout(dropout),
        )

    def forward(self, states):
        batch, experts, sequence, width = states.shape
        value = states.permute(0, 2, 1, 3).reshape(batch * sequence, experts, width)
        normalized = self.norm_attention(value)
        q, k, v = self.qkv(normalized).view(
            batch * sequence, experts, 3, self.heads, self.head_width
        ).permute(2, 0, 3, 1, 4).unbind(0)
        messages = F.scaled_dot_product_attention(
            q,
            k,
            v,
            dropout_p=self.dropout if self.training else 0.0,
            is_causal=False,
        )
        messages = messages.transpose(1, 2).contiguous().view(batch * sequence, experts, width)
        value = value + self.output(messages)
        value = value + self.mlp(self.norm_mlp(value))
        return value.view(batch, sequence, experts, width).permute(0, 2, 1, 3).contiguous()


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
        communication_heads=8,
        communication_ff=512,
        fusion_layers=20,
        fusion_width=1792,
        fusion_heads=16,
        fusion_ff=2048,
        dropout=0.0,
    ):
        super().__init__()
        if experts != 7:
            raise ValueError("The mutual architecture requires exactly seven networks.")
        if fusion_width != experts * expert_width:
            raise ValueError("Fusion width must equal seven times expert width.")
        if expert_width % expert_heads or expert_width % communication_heads:
            raise ValueError("Expert width must be divisible by attention head counts.")
        if fusion_width % fusion_heads:
            raise ValueError("Fusion width must be divisible by fusion head count.")

        self.vocab_size = vocab_size
        self.context_length = context_length
        self.expert_count = experts
        self.expert_width = expert_width
        self.fusion_width = fusion_width
        self.gradient_checkpointing = False

        self.token_embedding = nn.Embedding(vocab_size, expert_width)
        self.position_embedding = nn.Parameter(torch.zeros(1, context_length, expert_width))
        self.expert_identity = nn.Parameter(torch.empty(1, experts, 1, expert_width))
        nn.init.normal_(self.position_embedding, mean=0.0, std=0.02)
        nn.init.normal_(self.expert_identity, mean=0.0, std=0.02)

        self.experts = nn.ModuleList([
            nn.ModuleList([
                CausalBlock(expert_width, expert_heads, expert_ff, dropout)
                for _ in range(expert_layers)
            ])
            for _ in range(experts)
        ])
        self.communication = nn.ModuleList([
            MutualCommunication(expert_width, communication_heads, communication_ff, dropout)
            for _ in range(expert_layers)
        ])
        self.expert_norms = nn.ModuleList([nn.LayerNorm(expert_width) for _ in range(experts)])
        self.expert_head_biases = nn.ParameterList([
            nn.Parameter(torch.zeros(vocab_size)) for _ in range(experts)
        ])

        self.fusion_positions = nn.Parameter(torch.zeros(1, context_length, fusion_width))
        nn.init.normal_(self.fusion_positions, mean=0.0, std=0.02)
        self.fusion_blocks = nn.ModuleList([
            CausalBlock(fusion_width, fusion_heads, fusion_ff, dropout)
            for _ in range(fusion_layers)
        ])
        self.fusion_norm = nn.LayerNorm(fusion_width)
        self.output_projection = nn.Linear(fusion_width, expert_width, bias=False)
        self.output_norm = nn.LayerNorm(expert_width)
        self.output_bias = nn.Parameter(torch.zeros(vocab_size))

    def set_gradient_checkpointing(self, enabled=True):
        self.gradient_checkpointing = bool(enabled)

    def _apply_block(self, block, value):
        if self.gradient_checkpointing and self.training:
            return checkpoint(block, value, use_reentrant=False)
        return block(value)

    def encode_expert(self, input_ids, expert_index):
        if input_ids.ndim != 2:
            raise ValueError("input_ids must have shape [batch, sequence].")
        if input_ids.size(1) > self.context_length:
            raise ValueError("Input sequence exceeds configured context length.")
        if not 0 <= expert_index < self.expert_count:
            raise ValueError("expert_index must be between 0 and 6.")

        embedded = self.token_embedding(input_ids) + self.position_embedding[:, :input_ids.size(1)]
        state = embedded + self.expert_identity[:, expert_index]
        for block in self.experts[expert_index]:
            state = self._apply_block(block, state)
        return self.expert_norms[expert_index](state)

    def encode_all_experts(self, input_ids, use_communication=True):
        if input_ids.ndim != 2:
            raise ValueError("input_ids must have shape [batch, sequence].")
        batch, sequence = input_ids.shape
        if sequence > self.context_length:
            raise ValueError("Input sequence exceeds configured context length.")

        embedded = self.token_embedding(input_ids) + self.position_embedding[:, :sequence]
        states = embedded.unsqueeze(1) + self.expert_identity

        for layer_index in range(len(self.communication)):
            next_states = []
            for expert_index in range(self.expert_count):
                block = self.experts[expert_index][layer_index]
                next_states.append(self._apply_block(block, states[:, expert_index]))
            states = torch.stack(next_states, dim=1)
            if use_communication:
                states = self._apply_block(self.communication[layer_index], states)

        return torch.stack([
            self.expert_norms[index](states[:, index])
            for index in range(self.expert_count)
        ], dim=1)

    def forward_from_expert_states(self, expert_states):
        batch, experts, sequence, width = expert_states.shape
        if experts != self.expert_count or width != self.expert_width:
            raise ValueError("expert_states must have shape [batch, 7, sequence, expert_width].")
        if sequence > self.context_length:
            raise ValueError("Input sequence exceeds configured context length.")
        collective_state = expert_states.permute(0, 2, 1, 3).contiguous().view(
            batch, sequence, self.fusion_width
        )
        hidden = collective_state + self.fusion_positions[:, :sequence]
        for block in self.fusion_blocks:
            hidden = self._apply_block(block, hidden)
        hidden = self.fusion_norm(hidden)
        hidden = self.output_norm(self.output_projection(hidden))
        return F.linear(hidden, self.token_embedding.weight, self.output_bias)

    def forward(self, input_ids, return_aux=False, use_communication=True):
        expert_states = self.encode_all_experts(
            input_ids,
            use_communication=use_communication,
        )
        auxiliary_logits = None
        if return_aux:
            auxiliary_logits = torch.stack([
                F.linear(
                    expert_states[:, index],
                    self.token_embedding.weight,
                    self.expert_head_biases[index],
                )
                for index in range(self.expert_count)
            ], dim=1)
        logits = self.forward_from_expert_states(expert_states)
        if return_aux:
            return logits, auxiliary_logits
        return logits

    def forward_expert(self, input_ids, expert_index):
        state = self.encode_expert(input_ids, expert_index)
        return F.linear(
            state,
            self.token_embedding.weight,
            self.expert_head_biases[expert_index],
        )

    @torch.no_grad()
    def generate_all(self, input_ids, max_new_tokens=128, temperature=0.0, top_k=40):
        self.eval()
        sequences = [input_ids.clone() for _ in range(self.expert_count + 1)]
        original_batch = input_ids.size(0)
        for _ in range(max_new_tokens):
            batch = torch.cat([sequence[:, -self.context_length:] for sequence in sequences], dim=0)
            final_logits, auxiliary = self(batch, return_aux=True)
            next_tokens = []
            for index in range(self.expert_count + 1):
                start = index * original_batch
                end = start + original_batch
                if index == 0:
                    logits = final_logits[start:end, -1, :]
                else:
                    logits = auxiliary[start:end, index - 1, -1, :]
                if temperature <= 0:
                    token = logits.argmax(dim=-1, keepdim=True)
                else:
                    logits = logits / temperature
                    if top_k > 0:
                        values, _ = torch.topk(logits, min(top_k, logits.size(-1)))
                        logits[logits < values[:, -1:]] = -torch.inf
                    token = torch.multinomial(torch.softmax(logits, dim=-1), num_samples=1)
                next_tokens.append(token)
            sequences = [
                torch.cat([sequence, token], dim=1)
                for sequence, token in zip(sequences, next_tokens)
            ]
        return sequences

    @torch.no_grad()
    def generate(self, input_ids, max_new_tokens=128, temperature=0.8, top_k=40, expert_index=None):
        self.eval()
        generated = input_ids
        for _ in range(max_new_tokens):
            context = generated[:, -self.context_length:]
            if expert_index is None:
                logits = self(context)[:, -1, :]
            else:
                _, auxiliary = self(context, return_aux=True)
                if not 0 <= expert_index < self.expert_count:
                    raise ValueError("expert_index must be between 0 and 6.")
                logits = auxiliary[:, expert_index, -1, :]
            if temperature <= 0:
                next_token = logits.argmax(dim=-1, keepdim=True)
            else:
                logits = logits / temperature
                if top_k > 0:
                    values, _ = torch.topk(logits, min(top_k, logits.size(-1)))
                    logits[logits < values[:, -1:]] = -torch.inf
                probabilities = torch.softmax(logits, dim=-1)
                next_token = torch.multinomial(probabilities, num_samples=1)
            generated = torch.cat([generated, next_token], dim=1)
        return generated


def target_config():
    return {
        "vocab_size": 32768,
        "context_length": 2048,
        "experts": 7,
        "expert_layers": 10,
        "expert_width": 256,
        "expert_heads": 8,
        "expert_ff": 768,
        "communication_heads": 8,
        "communication_ff": 512,
        "fusion_layers": 20,
        "fusion_width": 1792,
        "fusion_heads": 16,
        "fusion_ff": 2048,
        "dropout": 0.0,
    }


def smoke_config():
    return {
        "vocab_size": 260,
        "context_length": 128,
        "experts": 7,
        "expert_layers": 2,
        "expert_width": 32,
        "expert_heads": 4,
        "expert_ff": 64,
        "communication_heads": 4,
        "communication_ff": 64,
        "fusion_layers": 2,
        "fusion_width": 224,
        "fusion_heads": 7,
        "fusion_ff": 256,
        "dropout": 0.0,
    }
