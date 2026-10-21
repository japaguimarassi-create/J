from dataclasses import dataclass


@dataclass(frozen=True)
class DetaConfig:
    target_parameters: int = 80_000
    conceptual_action_units: int = 10_000
    vocab_size: int = 256
    embedding_dim: int = 64
    hidden_dim: int = 88
    sequence_length: int = 128
    batch_size: int = 16
    learning_rate: float = 1e-3

    def validate(self) -> None:
        if self.target_parameters < 1:
            raise ValueError("target_parameters must be positive")
        if self.conceptual_action_units < 1:
            raise ValueError("conceptual_action_units must be positive")
        if self.vocab_size != 256:
            raise ValueError("The initial model uses UTF-8 bytes and requires vocab_size=256")
        if self.embedding_dim < 1 or self.hidden_dim < 1:
            raise ValueError("Model dimensions must be positive")
        if self.sequence_length < 2 or self.batch_size < 1:
            raise ValueError("Invalid training dimensions")
        if self.learning_rate <= 0:
            raise ValueError("learning_rate must be positive")
