import random

import torch


def wsd_multiplier(step, total_steps, warmup_steps, decay_ratio=0.1):
    if total_steps < 1 or step < 1 or step > total_steps:
        raise ValueError("step must be inside the training range.")
    if not 0.0 < decay_ratio <= 1.0:
        raise ValueError("decay_ratio must be in (0, 1].")

    warmup = min(max(0, warmup_steps), max(0, total_steps - 1))
    if warmup and step <= warmup:
        return step / warmup

    decay_steps = max(1, int(total_steps * decay_ratio))
    decay_start = max(warmup + 1, total_steps - decay_steps + 1)
    if step < decay_start:
        return 1.0

    decay_length = max(1, total_steps - decay_start + 1)
    progress = (step - decay_start + 1) / decay_length
    return max(0.0, 1.0 - progress)


def build_adamw(model, learning_rate, weight_decay, fused=False):
    decay_parameters = []
    no_decay_parameters = []
    for name, parameter in model.named_parameters():
        if not parameter.requires_grad:
            continue
        lowered = name.lower()
        excluded = (
            parameter.ndim < 2
            or "bias" in lowered
            or "norm" in lowered
            or "embedding" in lowered
            or "position" in lowered
            or "expert_identity" in lowered
        )
        (no_decay_parameters if excluded else decay_parameters).append(parameter)

    groups = []
    if decay_parameters:
        groups.append({"params": decay_parameters, "weight_decay": weight_decay})
    if no_decay_parameters:
        groups.append({"params": no_decay_parameters, "weight_decay": 0.0})
    if not groups:
        raise ValueError("No trainable parameters were supplied to AdamW.")

    arguments = {"lr": learning_rate, "betas": (0.9, 0.95), "eps": 1e-8}
    if fused:
        try:
            return torch.optim.AdamW(groups, fused=True, **arguments)
        except (TypeError, RuntimeError):
            pass
    return torch.optim.AdamW(groups, **arguments)


def capture_rng_state():
    state = {"python": random.getstate(), "torch": torch.get_rng_state()}
    if torch.cuda.is_available():
        state["cuda"] = torch.cuda.get_rng_state_all()
    return state


def restore_rng_state(state):
    if not state:
        return
    random.setstate(state["python"])
    torch.set_rng_state(state["torch"])
    if torch.cuda.is_available() and "cuda" in state:
        torch.cuda.set_rng_state_all(state["cuda"])
