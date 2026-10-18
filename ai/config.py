from dataclasses import asdict, dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class ModelConfig:
    vocab_size: int = 32000
    hidden_size: int = 4096
    num_layers: int = 43
    num_attention_heads: int = 32
    num_key_value_heads: int = 8
    intermediate_size: int = 15104
    max_seq_len: int = 2048
    rms_norm_eps: float = 1e-5
    rope_theta: float = 10000.0
    gradient_checkpointing: bool = True

    def validate(self):
        if self.vocab_size < 256:
            raise ValueError("vocab_size must be at least 256")
        if self.hidden_size <= 0 or self.num_layers <= 0:
            raise ValueError("Model dimensions must be positive")
        if self.num_attention_heads <= 0 or self.num_key_value_heads <= 0:
            raise ValueError("Attention head counts must be positive")
        if self.hidden_size % self.num_attention_heads:
            raise ValueError("hidden_size must be divisible by num_attention_heads")
        if self.num_attention_heads % self.num_key_value_heads:
            raise ValueError("num_attention_heads must be divisible by num_key_value_heads")
        if (self.hidden_size // self.num_attention_heads) % 2:
            raise ValueError("head dimension must be even for RoPE")
        if self.intermediate_size <= 0 or self.max_seq_len < 2:
            raise ValueError("intermediate_size must be positive and max_seq_len >= 2")
        if self.rms_norm_eps <= 0 or self.rope_theta <= 0:
            raise ValueError("Normalization epsilon and RoPE theta must be positive")

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_json(cls, path):
        values = json.loads(Path(path).read_text(encoding="utf-8"))
        config = cls(**values)
        config.validate()
        return config


def tiny_config(vocab_size=32000):
    return ModelConfig(
        vocab_size=vocab_size,
        hidden_size=128,
        num_layers=2,
        num_attention_heads=4,
        num_key_value_heads=2,
        intermediate_size=512,
        max_seq_len=128,
        gradient_checkpointing=False,
    )


def estimate_parameters(config):
    config.validate()
    hidden = config.hidden_size
    head_dim = hidden // config.num_attention_heads
    kv_width = config.num_key_value_heads * head_dim
    attention = 2 * hidden * hidden + 2 * hidden * kv_width
    mlp = 3 * hidden * config.intermediate_size
    norms_per_block = 2 * hidden
    embeddings = 2 * config.vocab_size * hidden
    final_norm = hidden
    return embeddings + config.num_layers * (attention + mlp + norms_per_block) + final_norm
