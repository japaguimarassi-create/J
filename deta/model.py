import torch
from torch import nn


class DetaByteGRU(nn.Module):
    """Small byte-level language model used as an experimental training baseline."""

    def __init__(self, vocab_size: int = 256, embedding_dim: int = 64, hidden_dim: int = 88):
        super().__init__()
        self.vocab_size = vocab_size
        self.embedding = nn.Embedding(vocab_size, embedding_dim)
        self.recurrent = nn.GRU(embedding_dim, hidden_dim, batch_first=True)
        self.output = nn.Linear(hidden_dim, vocab_size)

    def forward(self, tokens: torch.Tensor, state: torch.Tensor | None = None) -> tuple[torch.Tensor, torch.Tensor]:
        if tokens.dtype != torch.long:
            tokens = tokens.long()
        embedded = self.embedding(tokens)
        hidden, next_state = self.recurrent(embedded, state)
        return self.output(hidden), next_state

    def parameter_count(self, trainable_only: bool = True) -> int:
        params = self.parameters()
        if trainable_only:
            return sum(parameter.numel() for parameter in params if parameter.requires_grad)
        return sum(parameter.numel() for parameter in params)


def build_default_model() -> DetaByteGRU:
    return DetaByteGRU(vocab_size=256, embedding_dim=64, hidden_dim=88)
