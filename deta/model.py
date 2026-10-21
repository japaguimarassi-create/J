import torch
from torch import nn

from deta.config import DetaConfig


class DetaByteGRU(nn.Module):
    """Original 79,824-parameter baseline retained for comparisons."""

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


class DetaGroup(nn.Module):
    """One 80,000-parameter byte-language expert."""

    def __init__(self, vocab_size: int = 256, embedding_dim: int = 64, hidden_dim: int = 88):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embedding_dim)
        self.recurrent = nn.GRU(embedding_dim, hidden_dim, batch_first=True)
        self.hidden_scale = nn.Parameter(torch.zeros(hidden_dim))
        self.hidden_bias = nn.Parameter(torch.zeros(hidden_dim))
        self.output = nn.Linear(hidden_dim, vocab_size)

    def forward(self, tokens: torch.Tensor) -> torch.Tensor:
        if tokens.dtype != torch.long:
            tokens = tokens.long()
        hidden, _ = self.recurrent(self.embedding(tokens))
        hidden = hidden * (1.0 + torch.tanh(self.hidden_scale)) + self.hidden_bias
        return self.output(hidden)

    def parameter_count(self, trainable_only: bool = True) -> int:
        parameters = self.parameters()
        if trainable_only:
            return sum(parameter.numel() for parameter in parameters if parameter.requires_grad)
        return sum(parameter.numel() for parameter in parameters)


class DetaFiveGroupModel(nn.Module):
    """Five additive 80k groups trained in sequence, totaling exactly 400k parameters."""

    def __init__(
        self,
        groups: int = 5,
        vocab_size: int = 256,
        embedding_dim: int = 64,
        hidden_dim: int = 88,
    ):
        super().__init__()
        if groups != 5:
            raise ValueError("This Deta version is defined as exactly five training groups.")
        self.vocab_size = vocab_size
        self.group_count = groups
        self.groups = nn.ModuleList(
            [
                DetaGroup(vocab_size=vocab_size, embedding_dim=embedding_dim, hidden_dim=hidden_dim)
                for _ in range(groups)
            ]
        )
        for group in self.groups[1:]:
            nn.init.zeros_(group.output.weight)
            nn.init.zeros_(group.output.bias)

    def forward(
        self,
        tokens: torch.Tensor,
        active_groups: int | None = None,
        train_group: int | None = None,
    ) -> torch.Tensor:
        active = self.group_count if active_groups is None else active_groups
        if not 1 <= active <= self.group_count:
            raise ValueError(f"active_groups must be between 1 and {self.group_count}")
        if train_group is not None and not 0 <= train_group < active:
            raise ValueError("train_group must identify one of the active groups")

        total_logits = None
        for index, group in enumerate(self.groups[:active]):
            if train_group is not None and index != train_group:
                with torch.no_grad():
                    logits = group(tokens)
            else:
                logits = group(tokens)
            total_logits = logits if total_logits is None else total_logits + logits
        if total_logits is None:
            raise RuntimeError("The model must have at least one active group.")
        return total_logits

    def parameter_count(self, trainable_only: bool = True) -> int:
        parameters = self.parameters()
        if trainable_only:
            return sum(parameter.numel() for parameter in parameters if parameter.requires_grad)
        return sum(parameter.numel() for parameter in parameters)

    def group_parameter_count(self, group_index: int, trainable_only: bool = True) -> int:
        if not 0 <= group_index < self.group_count:
            raise IndexError("group_index is outside the five-group model")
        return self.groups[group_index].parameter_count(trainable_only=trainable_only)


def build_default_model() -> DetaByteGRU:
    return DetaByteGRU(vocab_size=256, embedding_dim=64, hidden_dim=88)


def build_grouped_model(config: DetaConfig | None = None) -> DetaFiveGroupModel:
    cfg = config or DetaConfig()
    cfg.validate()
    return DetaFiveGroupModel(
        groups=cfg.groups,
        vocab_size=cfg.vocab_size,
        embedding_dim=cfg.embedding_dim,
        hidden_dim=cfg.hidden_dim,
    )
