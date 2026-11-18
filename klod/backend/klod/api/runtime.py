from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import torch

from klod.neural import GPTModel, ModelConfig
from klod.tokenizer import BytePairTokenizer


class ModelUnavailable(RuntimeError):
    pass


class ModelRuntime:
    def __init__(self) -> None:
        self.model: GPTModel | None = None
        self.tokenizer: BytePairTokenizer | None = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.training_steps = 0
        self.parameter_count = 0

    def load(self) -> None:
        checkpoint_path = Path(os.getenv("KLOD_CHECKPOINT_PATH", "artifacts/checkpoints/latest.pt"))
        tokenizer_path = Path(os.getenv("KLOD_TOKENIZER_PATH", "artifacts/tokenizer.json"))
        if not checkpoint_path.is_file() or not tokenizer_path.is_file():
            raise ModelUnavailable("No trained Klod checkpoint and matching tokenizer are configured")
        checkpoint: dict[str, Any] = torch.load(checkpoint_path, map_location=self.device, weights_only=False)
        steps = int(checkpoint.get("training_steps", checkpoint.get("step", 0)))
        if steps < 1:
            raise ModelUnavailable("Checkpoint contains no completed optimizer step")
        tokenizer = BytePairTokenizer.load(tokenizer_path)
        if tokenizer.vocab_size != int(checkpoint["tokenizer_vocab_size"]):
            raise ModelUnavailable("Checkpoint and tokenizer vocabulary sizes do not match")
        model = GPTModel(ModelConfig(**checkpoint["model_config"])).to(self.device)
        model.load_state_dict(checkpoint["model_state"])
        model.eval()
        self.model, self.tokenizer = model, tokenizer
        self.training_steps, self.parameter_count = steps, model.parameter_count()

    def generate(self, prompt: str, max_new_tokens: int, temperature: float) -> str:
        if self.model is None or self.tokenizer is None:
            raise ModelUnavailable("Klod model is not loaded")
        encoded = self.tokenizer.encode(prompt, add_bos=True)
        tokens = torch.tensor([encoded], dtype=torch.long, device=self.device)
        output = self.model.generate(tokens, max_new_tokens=max_new_tokens, temperature=temperature, top_k=40, eos_token_id=self.tokenizer.special_token_ids["<eos>"])[0].tolist()
        return self.tokenizer.decode(output[len(encoded):], skip_special_tokens=True, errors="replace")
