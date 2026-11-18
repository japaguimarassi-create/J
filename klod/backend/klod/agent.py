from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from klod.api.runtime import ModelRuntime
from klod.tools.workspace import CoderWorkspace


@dataclass(frozen=True)
class KlodContext:
    user_id: str
    permissions: frozenset[str] = frozenset()
    approved_operations: frozenset[str] = frozenset()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class KlodResponse:
    text: str
    model_status: str
    training_steps: int
    parameter_count: int


class KlodAgent:
    """The single Klod identity and model, with coding as an integrated capability."""

    def __init__(self, runtime: ModelRuntime, coder: CoderWorkspace | None = None) -> None:
        self.runtime = runtime
        self.coder = coder

    def respond(self, message: str, max_new_tokens: int = 256, temperature: float = 0.8) -> KlodResponse:
        if not isinstance(message, str) or not message.strip():
            raise ValueError("A non-empty user message is required")
        text = self.runtime.generate(message, max_new_tokens=max_new_tokens, temperature=temperature)
        return KlodResponse(
            text=text,
            model_status="experimental",
            training_steps=self.runtime.training_steps,
            parameter_count=self.runtime.parameter_count,
        )

    def read_project_file(self, relative_path: str, context: KlodContext) -> str:
        if self.coder is None:
            raise RuntimeError("Klod coder workspace is not configured")
        return self.coder.read_text(relative_path, context)

    def write_project_file(self, relative_path: str, content: str, context: KlodContext) -> None:
        if self.coder is None:
            raise RuntimeError("Klod coder workspace is not configured")
        self.coder.write_text(relative_path, content, context)
