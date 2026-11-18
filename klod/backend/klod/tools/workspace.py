from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from klod.agent import KlodContext


class WorkspacePermissionError(PermissionError):
    pass


class CoderWorkspace:
    def __init__(self, root: str | Path, max_file_bytes: int = 1_000_000) -> None:
        if max_file_bytes < 1:
            raise ValueError("max_file_bytes must be positive")
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.max_file_bytes = max_file_bytes

    @staticmethod
    def _safe_segment(value: str, label: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", value):
            raise WorkspacePermissionError(f"Invalid {label}")
        return value

    def _workspace_root(self, context: KlodContext) -> Path:
        user_id = self._safe_segment(str(context.user_id), "user identifier")
        workspace_id = self._safe_segment(str(context.metadata.get("workspace_id", "default")), "workspace identifier")
        workspace = (self.root / user_id / workspace_id).resolve()
        if not workspace.is_relative_to(self.root):
            raise WorkspacePermissionError("Workspace path escapes the configured root")
        workspace.mkdir(parents=True, exist_ok=True)
        return workspace

    def _resolve(self, relative_path: str, context: KlodContext) -> Path:
        if not relative_path or Path(relative_path).is_absolute():
            raise ValueError("A relative workspace path is required")
        if "\x00" in relative_path or "\\" in relative_path:
            raise ValueError("Workspace paths must use normalized forward slashes")
        workspace = self._workspace_root(context)
        target = (workspace / relative_path).resolve()
        if not target.is_relative_to(workspace):
            raise WorkspacePermissionError("Path escapes the authorized workspace")
        return target

    def list_files(self, context: KlodContext, limit: int = 500) -> list[dict[str, str | int]]:
        if "filesystem:read" not in context.permissions:
            raise WorkspacePermissionError("Filesystem read permission is required")
        workspace = self._workspace_root(context)
        files: list[dict[str, str | int]] = []
        for target in workspace.rglob("*"):
            if not target.is_file():
                continue
            resolved = target.resolve()
            if not resolved.is_relative_to(workspace):
                continue
            relative = resolved.relative_to(workspace).as_posix()
            size = resolved.stat().st_size
            files.append({"path": relative, "size": size})
            if len(files) >= max(1, min(limit, 500)):
                break
        return sorted(files, key=lambda item: str(item["path"]).lower())

    def read_text(self, relative_path: str, context: KlodContext) -> str:
        if "filesystem:read" not in context.permissions:
            raise WorkspacePermissionError("Filesystem read permission is required")
        target = self._resolve(relative_path, context)
        if not target.is_file():
            raise FileNotFoundError(relative_path)
        if target.stat().st_size > self.max_file_bytes:
            raise ValueError("File exceeds the configured size limit")
        return target.read_text(encoding="utf-8")

    def write_text(self, relative_path: str, content: str, context: KlodContext) -> None:
        if "filesystem:write" not in context.permissions:
            raise WorkspacePermissionError("Filesystem write permission is required")
        if "filesystem:write:" + relative_path not in context.approved_operations:
            raise WorkspacePermissionError("This exact file write has not been approved")
        encoded = content.encode("utf-8")
        if len(encoded) > self.max_file_bytes:
            raise ValueError("Content exceeds the configured size limit")
        target = self._resolve(relative_path, context)
        target.parent.mkdir(parents=True, exist_ok=True)
        workspace = self._workspace_root(context)
        if not target.parent.resolve().is_relative_to(workspace):
            raise WorkspacePermissionError("Parent directory escapes the authorized workspace")
        descriptor, temporary_name = tempfile.mkstemp(prefix=".klod-", suffix=".tmp", dir=target.parent)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
        finally:
            if temporary.exists():
                temporary.unlink()
