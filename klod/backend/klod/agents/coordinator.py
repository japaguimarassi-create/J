from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable


@dataclass(frozen=True)
class AgentContext:
    task_id: str
    permissions: frozenset[str] = frozenset()
    approved_operations: frozenset[str] = frozenset()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentResult:
    agent: str
    status: str
    output: Any
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExecutionReport:
    task_id: str
    status: str
    results: tuple[AgentResult, ...]
    elapsed_seconds: float
    error: str | None = None


AgentHandler = Callable[[AgentContext, Any], Awaitable[AgentResult]]


class AgentCoordinator:
    """Bounded sequential executor for real registered agent modules."""

    def __init__(self, max_steps: int = 8, timeout_seconds: float = 30.0) -> None:
        if max_steps < 1 or timeout_seconds <= 0:
            raise ValueError("Execution limits must be positive")
        self.max_steps = max_steps
        self.timeout_seconds = timeout_seconds
        self._agents: dict[str, AgentHandler] = {}

    def register(self, name: str, handler: AgentHandler) -> None:
        if not name or name in self._agents:
            raise ValueError("Agent name must be non-empty and unique")
        self._agents[name] = handler

    async def run(
        self,
        task: Any,
        context: AgentContext | None = None,
        sequence: tuple[str, ...] | None = None,
    ) -> ExecutionReport:
        task_id = context.task_id if context else str(uuid.uuid4())
        active_context = context or AgentContext(task_id=task_id)
        selected = sequence if sequence is not None else tuple(self._agents)
        if not selected:
            return ExecutionReport(task_id, "rejected", (), 0.0, "No agents registered")
        if len(selected) > self.max_steps:
            return ExecutionReport(task_id, "rejected", (), 0.0, "Step budget exceeded")
        started = time.monotonic()
        results: list[AgentResult] = []
        current_input = task
        try:
            for name in selected:
                handler = self._agents.get(name)
                if handler is None:
                    raise LookupError(f"Unknown agent: {name}")
                remaining = self.timeout_seconds - (time.monotonic() - started)
                if remaining <= 0:
                    raise TimeoutError("Agent execution deadline exceeded")
                result = await asyncio.wait_for(handler(active_context, current_input), timeout=remaining)
                if not isinstance(result, AgentResult) or result.agent != name:
                    raise TypeError(f"Agent {name} returned an invalid result")
                results.append(result)
                if result.status != "ok":
                    return ExecutionReport(task_id, "failed", tuple(results), time.monotonic() - started, f"Agent {name} did not complete")
                current_input = result.output
            return ExecutionReport(task_id, "completed", tuple(results), time.monotonic() - started)
        except asyncio.TimeoutError:
            return ExecutionReport(task_id, "failed", tuple(results), time.monotonic() - started, "Agent execution timed out")
        except (LookupError, TimeoutError, TypeError, ValueError) as error:
            return ExecutionReport(task_id, "failed", tuple(results), time.monotonic() - started, str(error))
