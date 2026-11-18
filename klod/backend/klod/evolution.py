from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from klod.neural.model import ModelConfig


@dataclass(frozen=True)
class GrowthDecision:
    approved: bool
    reason: str
    source_step: int
    target_config: ModelConfig | None
    estimated_parameters: int | None


@dataclass(frozen=True)
class GrowthPolicy:
    interval_steps: int = 50_000
    layer_increment: int = 1
    feed_forward_multiplier: float = 1.25
    context_increment: int = 128
    max_context: int = 4096
    max_parameters: int = 100_000_000
    max_validation_regression: float = 0.02

    def __post_init__(self) -> None:
        if self.interval_steps < 1 or self.layer_increment < 1 or self.context_increment < 1:
            raise ValueError("Growth intervals and increments must be positive")
        if self.feed_forward_multiplier <= 1 or self.max_context < 2 or self.max_parameters < 1:
            raise ValueError("Invalid growth policy limits")
        if not 0 <= self.max_validation_regression < 1:
            raise ValueError("Validation regression tolerance must be in [0, 1)")

    @staticmethod
    def estimate_parameters(config: ModelConfig) -> int:
        width = config.d_model
        feed_forward = config.d_ff
        per_layer = 4 * width * width + 2 * width * feed_forward + feed_forward + 2 * width
        embeddings_and_output = config.vocab_size * width
        final_norm = width
        return embeddings_and_output + config.n_layers * per_layer + final_norm

    def propose(
        self,
        current: ModelConfig,
        training_steps: int,
        last_growth_step: int,
        best_validation_loss: float,
        candidate_validation_loss: float,
    ) -> GrowthDecision:
        def reject(reason: str) -> GrowthDecision:
            return GrowthDecision(False, reason, training_steps, None, None)

        if training_steps < 1 or last_growth_step < 0:
            return reject("Invalid training-step metadata")
        if training_steps - last_growth_step < self.interval_steps:
            return reject("Growth interval has not elapsed")
        if not math.isfinite(best_validation_loss) or best_validation_loss <= 0:
            return reject("A finite positive best validation loss is required")
        if not math.isfinite(candidate_validation_loss) or candidate_validation_loss <= 0:
            return reject("A finite positive candidate validation loss is required")
        allowed_loss = best_validation_loss * (1.0 + self.max_validation_regression)
        if candidate_validation_loss > allowed_loss:
            return reject("Candidate quality does not meet the validation gate")

        next_width = max(64, int(math.ceil(current.d_ff * self.feed_forward_multiplier / 64)) * 64)
        next_context = min(self.max_context, current.max_seq_len + self.context_increment)
        target = ModelConfig(
            vocab_size=current.vocab_size,
            max_seq_len=next_context,
            d_model=current.d_model,
            n_heads=current.n_heads,
            n_layers=current.n_layers + self.layer_increment,
            d_ff=next_width,
            rope_base=current.rope_base,
        )
        estimate = self.estimate_parameters(target)
        if estimate > self.max_parameters:
            return reject("Proposed model exceeds the configured parameter budget")
        return GrowthDecision(
            True,
            "Milestone elapsed and validation quality gate passed",
            training_steps,
            target,
            estimate,
        )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
