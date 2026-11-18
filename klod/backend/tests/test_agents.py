import asyncio

import pytest

from klod.agents.coordinator import AgentContext, AgentCoordinator, AgentResult
from klod.agents.workspace import Workspace, WorkspacePermissionError


def test_coordinator_runs_real_registered_modules_in_order():
    coordinator = AgentCoordinator(max_steps=3)
    events = []

    async def first(context, value):
        events.append(("first", value))
        return AgentResult("first", "ok", value + 1, ("incremented",))

    async def second(context, value):
        events.append(("second", value))
        return AgentResult("second", "ok", value * 2)

    coordinator.register("first", first)
    coordinator.register("second", second)
    report = asyncio.run(coordinator.run(4, sequence=("first", "second")))
    assert report.status == "completed"
    assert events == [("first", 4), ("second", 5)]
    assert report.results[-1].output == 10


def test_coordinator_enforces_step_budget():
    coordinator = AgentCoordinator(max_steps=1)
    report = asyncio.run(coordinator.run("task", sequence=("missing", "missing")))
    assert report.status == "rejected"
    assert report.error == "Step budget exceeded"


def test_coordinator_stops_on_deadline():
    coordinator = AgentCoordinator(timeout_seconds=0.01)

    async def slow(context, value):
        await asyncio.sleep(0.1)
        return AgentResult("slow", "ok", value)

    coordinator.register("slow", slow)
    report = asyncio.run(coordinator.run("task"))
    assert report.status == "failed"
    assert "deadline" in (report.error or "").lower() or "timed out" in (report.error or "").lower()


def test_workspace_read_write_permissions_and_approval(tmp_path):
    workspace = Workspace(tmp_path)
    allowed = AgentContext(
        task_id="test",
        permissions=frozenset({"filesystem:read", "filesystem:write"}),
        approved_operations=frozenset({"filesystem:write:notes/result.txt"}),
    )
    with pytest.raises(WorkspacePermissionError):
        workspace.write_text("notes/result.txt", "blocked", AgentContext(task_id="no-permission"))
    with pytest.raises(WorkspacePermissionError):
        workspace.write_text("notes/result.txt", "blocked", AgentContext(task_id="no-approval", permissions=frozenset({"filesystem:write"})))
    workspace.write_text("notes/result.txt", "authorized", allowed)
    assert workspace.read_text("notes/result.txt", allowed) == "authorized"


def test_workspace_rejects_path_traversal(tmp_path):
    workspace = Workspace(tmp_path / "workspace")
    context = AgentContext(task_id="test", permissions=frozenset({"filesystem:read"}))
    with pytest.raises(WorkspacePermissionError):
        workspace.read_text("../secret.txt", context)
