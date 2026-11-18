import pytest

from klod.agent import KlodAgent, KlodContext
from klod.tools.workspace import CoderWorkspace, WorkspacePermissionError


class FakeRuntime:
    training_steps = 12
    parameter_count = 1234

    def generate(self, prompt, max_new_tokens, temperature):
        return "Klod response to: " + prompt


def test_there_is_one_klod_agent_with_one_model_runtime(tmp_path):
    coder = CoderWorkspace(tmp_path)
    agent = KlodAgent(FakeRuntime(), coder)
    result = agent.respond("Explain this function")
    assert result.text == "Klod response to: Explain this function"
    assert result.training_steps == 12
    assert result.parameter_count == 1234


def test_coder_is_an_integrated_capability_not_a_separate_agent(tmp_path):
    agent = KlodAgent(FakeRuntime(), CoderWorkspace(tmp_path))
    context = KlodContext(
        user_id="user-1",
        permissions=frozenset({"filesystem:read", "filesystem:write"}),
        approved_operations=frozenset({"filesystem:write:src/main.py"}),
    )
    with pytest.raises(WorkspacePermissionError):
        agent.write_project_file("src/main.py", "print('blocked')", KlodContext(user_id="user-1"))
    agent.write_project_file("src/main.py", "print('approved')", context)
    assert agent.read_project_file("src/main.py", context) == "print('approved')"


def test_coder_requires_explicit_path_level_approval(tmp_path):
    agent = KlodAgent(FakeRuntime(), CoderWorkspace(tmp_path))
    context = KlodContext(user_id="user-1", permissions=frozenset({"filesystem:write"}))
    with pytest.raises(WorkspacePermissionError):
        agent.write_project_file("../outside.txt", "blocked", context)


def test_coder_workspaces_are_isolated_by_user_and_project(tmp_path):
    workspace = CoderWorkspace(tmp_path)
    agent = KlodAgent(FakeRuntime(), workspace)
    user_one_project_a = KlodContext(
        user_id="user-1",
        permissions=frozenset({"filesystem:read", "filesystem:write"}),
        approved_operations=frozenset({"filesystem:write:src/main.py"}),
        metadata={"workspace_id": "project-a"},
    )
    user_one_project_b = KlodContext(
        user_id="user-1",
        permissions=frozenset({"filesystem:read", "filesystem:write"}),
        approved_operations=frozenset({"filesystem:write:src/main.py"}),
        metadata={"workspace_id": "project-b"},
    )
    user_two_project_a = KlodContext(
        user_id="user-2",
        permissions=frozenset({"filesystem:read", "filesystem:write"}),
        approved_operations=frozenset({"filesystem:write:src/main.py"}),
        metadata={"workspace_id": "project-a"},
    )

    agent.write_project_file("src/main.py", "user one project a", user_one_project_a)
    agent.write_project_file("src/main.py", "user one project b", user_one_project_b)
    agent.write_project_file("src/main.py", "user two project a", user_two_project_a)

    assert agent.read_project_file("src/main.py", user_one_project_a) == "user one project a"
    assert agent.read_project_file("src/main.py", user_one_project_b) == "user one project b"
    assert agent.read_project_file("src/main.py", user_two_project_a) == "user two project a"
    assert agent.list_project_files(user_one_project_a) == [{"path": "src/main.py", "size": 17}]
