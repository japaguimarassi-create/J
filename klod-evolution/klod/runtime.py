from pathlib import Path
from typing import Optional

import torch

from .model import ByteTokenizer, KlodModel, ModelConfig


class KlodRuntime:
    def __init__(self, checkpoint: Optional[str] = None, device: Optional[str] = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = ByteTokenizer()
        self.model: Optional[KlodModel] = None
        self.training_info: Optional[dict] = None
        if checkpoint:
            self.load(checkpoint)

    @property
    def trained(self) -> bool:
        return self.model is not None

    def load(self, checkpoint: str) -> None:
        path = Path(checkpoint)
        if not path.is_file():
            raise FileNotFoundError(path)
        state = torch.load(path, map_location=self.device, weights_only=False)
        config = ModelConfig(**state["config"])
        model = KlodModel(config)
        model.load_state_dict(state["state_dict"])
        model.to(self.device).eval()
        self.model = model
        self.training_info = state.get("training", {})

    def chat(self, message: str, max_new_tokens: int = 180) -> str:
        if self.model is None:
            raise RuntimeError("KLOD ainda não possui checkpoint treinado. Execute klod.train primeiro.")
        prompt = f"\nUsuário: {message}\nKLOD:"
        ids = torch.tensor([self.tokenizer.encode(prompt, add_eos=False)], dtype=torch.long, device=self.device)
        output = self.model.generate(ids, max_new_tokens=max_new_tokens)
        return self.tokenizer.decode(output[0, ids.size(1):].tolist()).strip()
