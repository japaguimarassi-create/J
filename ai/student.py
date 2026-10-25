from __future__ import annotations

from pathlib import Path
from typing import Any

import torch
import torch.nn as nn
import torch.nn.functional as F

VOCAB_SIZE = 7000
BLOCK_SIZE = 256
D_MODEL = 32
N_HEADS = 4
N_LAYERS = 2
FF_DIM = 64
RELATIVE_BUCKETS = 80
PAD_ID, BOS_ID, EOS_ID, UNK_ID = 0, 1, 2, 3
EXPECTED_PARAMS = 249_984


class CausalSelfAttention(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.qkv = nn.Linear(D_MODEL, 3 * D_MODEL)
        self.proj = nn.Linear(D_MODEL, D_MODEL)
        self.relative_bias = nn.Parameter(torch.zeros(N_HEADS, RELATIVE_BUCKETS))
        positions = torch.arange(BLOCK_SIZE)
        relative = positions[None, :] - positions[:, None]
        self.register_buffer("relative_buckets", (relative + 39).clamp(0, RELATIVE_BUCKETS - 1), persistent=False)
        causal = torch.tril(torch.ones(BLOCK_SIZE, BLOCK_SIZE, dtype=torch.bool))
        self.register_buffer("causal_mask", causal, persistent=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        batch, length, _ = x.shape
        qkv = self.qkv(x).view(batch, length, 3, N_HEADS, D_MODEL // N_HEADS)
        q, k, v = qkv.unbind(dim=2)
        q, k, v = q.transpose(1, 2), k.transpose(1, 2), v.transpose(1, 2)
        scores = (q @ k.transpose(-2, -1)) * ((D_MODEL // N_HEADS) ** -0.5)
        buckets = self.relative_buckets[:length, :length]
        scores = scores + self.relative_bias[:, buckets].unsqueeze(0)
        scores = scores.masked_fill(~self.causal_mask[:length, :length], torch.finfo(scores.dtype).min)
        weights = F.softmax(scores, dim=-1)
        output = (weights @ v).transpose(1, 2).contiguous().view(batch, length, D_MODEL)
        return self.proj(output)


class TransformerBlock(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.ln1 = nn.LayerNorm(D_MODEL)
        self.attention = CausalSelfAttention()
        self.ln2 = nn.LayerNorm(D_MODEL)
        self.fc1 = nn.Linear(D_MODEL, FF_DIM)
        self.fc2 = nn.Linear(FF_DIM, D_MODEL)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.attention(self.ln1(x))
        return x + self.fc2(F.gelu(self.fc1(self.ln2(x))))


class ForgeStudent(nn.Module):
    """Transformer causal compacto com exatamente 249.984 parâmetros."""
    def __init__(self) -> None:
        super().__init__()
        self.token_embedding = nn.Embedding(VOCAB_SIZE, D_MODEL)
        self.position_embedding = nn.Embedding(BLOCK_SIZE, D_MODEL)
        self.blocks = nn.ModuleList([TransformerBlock() for _ in range(N_LAYERS)])
        self.final_norm = nn.LayerNorm(D_MODEL)

    def forward(self, token_ids: torch.Tensor) -> torch.Tensor:
        if token_ids.shape[1] > BLOCK_SIZE:
            token_ids = token_ids[:, -BLOCK_SIZE:]
        length = token_ids.shape[1]
        positions = torch.arange(length, device=token_ids.device)
        hidden = self.token_embedding(token_ids) + self.position_embedding(positions)[None, :, :]
        for block in self.blocks:
            hidden = block(hidden)
        return F.linear(self.final_norm(hidden), self.token_embedding.weight)

    def count_parameters(self) -> int:
        return sum(parameter.numel() for parameter in self.parameters() if parameter.requires_grad)


class ByteBPETokenizer:
    def __init__(self, token_bytes: list[bytes], merges: list[tuple[int, int, int]]) -> None:
        if len(token_bytes) != VOCAB_SIZE:
            raise ValueError("Tokenizer precisa ter exatamente 7000 tokens.")
        self.token_bytes, self.merges = token_bytes, merges

    @classmethod
    def train(cls, texts: list[str]) -> "ByteBPETokenizer":
        from collections import Counter
        token_bytes = [b"", b"", b"", b""] + [bytes([value]) for value in range(256)]
        sequences = [[BOS_ID] + [byte + 4 for byte in text.encode("utf-8", errors="replace")] + [EOS_ID] for text in texts]
        merges: list[tuple[int, int, int]] = []
        used_pairs: set[tuple[int, int]] = set()
        while len(token_bytes) < VOCAB_SIZE:
            counts: Counter[tuple[int, int]] = Counter()
            for sequence in sequences:
                for left, right in zip(sequence, sequence[1:]):
                    if left >= 4 and right >= 4:
                        counts[(left, right)] += 1
            best_pair = min(counts, key=lambda pair: (-counts[pair], pair[0], pair[1])) if counts else None
            if best_pair is None or counts[best_pair] < 2 or best_pair in used_pairs:
                break
            left, right = best_pair
            new_id = len(token_bytes)
            token_bytes.append(token_bytes[left] + token_bytes[right])
            merges.append((left, right, new_id))
            used_pairs.add(best_pair)
            for index, sequence in enumerate(sequences):
                output: list[int] = []
                cursor = 0
                while cursor < len(sequence):
                    if cursor + 1 < len(sequence) and sequence[cursor] == left and sequence[cursor + 1] == right:
                        output.append(new_id)
                        cursor += 2
                    else:
                        output.append(sequence[cursor])
                        cursor += 1
                sequences[index] = output
        for left in range(4, 260):
            for right in range(4, 260):
                if len(token_bytes) >= VOCAB_SIZE:
                    break
                pair = (left, right)
                if pair in used_pairs:
                    continue
                new_id = len(token_bytes)
                token_bytes.append(token_bytes[left] + token_bytes[right])
                merges.append((left, right, new_id))
                used_pairs.add(pair)
            if len(token_bytes) >= VOCAB_SIZE:
                break
        if len(token_bytes) != VOCAB_SIZE:
            raise RuntimeError("Falha ao construir o vocabulário fixo.")
        return cls(token_bytes, merges)

    def encode(self, text: str, add_special: bool = False) -> list[int]:
        ids = [byte + 4 for byte in text.encode("utf-8", errors="replace")]
        for left, right, new_id in self.merges:
            output: list[int] = []
            cursor = 0
            while cursor < len(ids):
                if cursor + 1 < len(ids) and ids[cursor] == left and ids[cursor + 1] == right:
                    output.append(new_id)
                    cursor += 2
                else:
                    output.append(ids[cursor])
                    cursor += 1
            ids = output
        return ([BOS_ID] + ids + [EOS_ID]) if add_special else ids

    def decode(self, ids: list[int]) -> str:
        raw = b"".join(self.token_bytes[token_id] for token_id in ids if 4 <= token_id < len(self.token_bytes))
        return raw.decode("utf-8", errors="replace")

    def to_dict(self) -> dict[str, Any]:
        return {"token_bytes_hex":[token.hex() for token in self.token_bytes],"merges":self.merges}

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ByteBPETokenizer":
        tokens = [bytes.fromhex(item) for item in value["token_bytes_hex"]]
        merges = [tuple(int(number) for number in item) for item in value["merges"]]
        return cls(tokens, merges)


def load_checkpoint(path: str | Path) -> tuple[ForgeStudent, ByteBPETokenizer]:
    try:
        saved = torch.load(path, map_location="cpu", weights_only=False)
    except TypeError:
        saved = torch.load(path, map_location="cpu")
    model = ForgeStudent()
    model.load_state_dict(saved["model_state"])
    if model.count_parameters() != EXPECTED_PARAMS:
        raise RuntimeError("Contagem de parâmetros inesperada.")
    model.eval()
    return model, ByteBPETokenizer.from_dict(saved["tokenizer"])


@torch.no_grad()
def generate_text(model: ForgeStudent, tokenizer: ByteBPETokenizer, prompt: str, max_new_tokens: int = 96) -> str:
    device = next(model.parameters()).device
    ids = [BOS_ID] + tokenizer.encode(prompt)
    sequence = torch.tensor([ids[-BLOCK_SIZE:]], dtype=torch.long, device=device)
    generated: list[int] = []
    model.eval()
    for _ in range(max(1, min(180, max_new_tokens))):
        logits = model(sequence)[:, -1, :]
        logits[:, :4] = torch.finfo(logits.dtype).min
        next_id = int(torch.argmax(logits, dim=-1).item())
        if next_id in (EOS_ID, PAD_ID):
            break
        generated.append(next_id)
        sequence = torch.cat([sequence, torch.tensor([[next_id]], dtype=torch.long, device=device)], dim=1)[:, -BLOCK_SIZE:]
    return tokenizer.decode(generated).strip()


if __name__ == "__main__":
    model = ForgeStudent()
    print({"trainable_parameters":model.count_parameters(),"expected":EXPECTED_PARAMS,"valid":model.count_parameters()==EXPECTED_PARAMS})
