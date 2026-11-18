from __future__ import annotations

import os
from pathlib import Path

from .coordinator import AgentContext


class WorkspacePermissionError(PermissionError):
    pass


class Workspace:
    """Path-confined text workspace; writes require permission and explicit approval."""

    def __init__(self, root: str | Path, max_file_bytes: int = 1_000_000) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.max_file_bytes = max_file_bytes

    def _resolve(self, relative_path: str) -> Path:
        if not relative_path or Path(relative_path).is_absolute():
            raise ValueError("A relative workspace path is required")
        target = (self.root / relative_path).resolve()
        if not target.is_relative_to(self.root):
            raise WorkspacePermissionError("Path escapes the authorized workspace")
        return target

    def read_text(self, relative_path: str, context: AgentContext) -> str:
        if "filesystem:read" not in context.permissions:
            raise WorkspacePermissionError("Filesystem read permission is required")
        target = self._resolve(relative_path)
        if not target.is_file():
            raise FileNotFoundError(relative_path)
        if target.stat().st_size > self.max_file_bytes:
            raise ValueError("File exceeds the configured size limit")
        return target.read_text(encoding="utf-8")

    def write_text(self, relative_path: str, content: str, context: AgentContext) -> None:
        if "filesystem:write" not in context.permissions:
            raise WorkspacePermissionError("Filesystem write permission is required")
        if "filesystem:write:" + relative_path not in context.approved_operations:
            raise WorkspacePermissionError("This exact file write has not been approved")
        encoded = content.encode("utf-8")
        if len(encoded) > self.max_file_bytes:
            raise ValueError("Content exceeds the configured size limit")
        target = self._resolve(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        resolved_parent = target.parent.resolve()
        if not resolved_parent.is_relative_to(self.root):
            raise WorkspacePermissionError("Parent directory escapes the authorized workspace")
        temporary = target.with_name(target.name + ".klod-tmp")
        try:
            temporary.write_bytes(encoded)
            os.replace(temporary, target)
        finally:
            if temporary.exists():
                temporary.unlink()
