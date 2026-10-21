from pathlib import Path

import torch

from deta.config import DetaConfig
from deta.model import build_grouped_model


def generate_completion(
    checkpoint_path: str | Path,
    prompt: str,
    max_new_tokens: int = 160,
    temperature: float = 0.8,
    top_k: int = 24,
    seed: int = 42,
    device: str | None = None,
) -> dict[str, object]:
    if not isinstance(prompt, str):
        raise TypeError("prompt must be a string")
    if not 1 <= max_new_tokens <= 512:
        raise ValueError("max_new_tokens must be between 1 and 512")
    if not 0.05 <= temperature <= 2.0:
        raise ValueError("temperature must be between 0.05 and 2.0")
    if not 1 <= top_k <= 64:
        raise ValueError("top_k must be between 1 and 64")
    if seed < 0:
        raise ValueError("seed must be non-negative")

    source = Path(checkpoint_path).expanduser()
    if not source.is_file():
        raise FileNotFoundError(f"Model checkpoint does not exist: {source}")
    selected_device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    if selected_device == "cuda" and not torch.cuda.is_available():
        raise ValueError("CUDA was requested but is not available.")

    checkpoint = torch.load(source, map_location=selected_device, weights_only=True)
    if not isinstance(checkpoint, dict) or checkpoint.get("model_type") != "DetaFiveGroupModel":
        raise ValueError("Expected a DetaFiveGroupModel checkpoint.")
    configuration = checkpoint.get("config")
    state_dict = checkpoint.get("model_state_dict")
    if not isinstance(configuration, dict) or not isinstance(state_dict, dict):
        raise ValueError("Checkpoint is missing its model configuration or weights.")

    config = DetaConfig(**configuration)
    config.validate()
    model = build_grouped_model(config).to(selected_device)
    model.load_state_dict(state_dict, strict=True)
    completed_groups = int(checkpoint.get("groups_completed", config.groups))
    if not 1 <= completed_groups <= config.groups:
        raise ValueError("Checkpoint has an invalid completed-group count.")
    model.eval()

    prompt_bytes = prompt.encode("utf-8") or b"\n"
    context = torch.tensor(list(prompt_bytes[-config.sequence_length:]), dtype=torch.long, device=selected_device)
    generator = torch.Generator(device=selected_device)
    generator.manual_seed(seed)
    output_bytes = bytearray()

    with torch.no_grad():
        for _ in range(max_new_tokens):
            tokens = context.unsqueeze(0)
            logits = model(tokens, active_groups=completed_groups)[0, -1, :]
            logits = logits / temperature
            values, indices = torch.topk(logits, k=min(top_k, logits.numel()))
            probabilities = torch.softmax(values, dim=-1)
            if top_k == 1:
                next_token = indices[0]
            else:
                selected = torch.multinomial(probabilities, num_samples=1, generator=generator)
                next_token = indices[selected[0]]
            byte_value = int(next_token.item())
            output_bytes.append(byte_value)
            context = torch.cat(
                [context, torch.tensor([byte_value], dtype=torch.long, device=selected_device)]
            )[-config.sequence_length:]

    return {
        "prompt": prompt,
        "completion": output_bytes.decode("utf-8", errors="replace"),
        "parameters": model.parameter_count(),
        "groups_used": completed_groups,
        "new_tokens": max_new_tokens,
        "temperature": temperature,
        "top_k": top_k,
        "seed": seed,
        "device": selected_device,
        "checkpoint": str(source),
        "mode": "local byte-level model completion; experimental, not factual QA",
    }
