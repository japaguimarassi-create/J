from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from klod.agent import KlodContext


class WorkspacePermissionError(PermissionError):
    pass


class CoderWorkspace:
    """Path-confined text workspace; writes require permission and exact approval."""

    def __init__(self, root: str | Path, max_file_bytes: int = 1_000_000) -> None:
        if max_file_bytes < 1:
            raise ValueError("max_file_bytes must be positive")
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

    def read_text(self, relative_path: str, context: KlodContext) -> str:
        if "filesystem:read" not in context.permissions:
            raise WorkspacePermissionError("Filesystem read permission is required")
        target = self._resolve(relative_path)
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
        target = self._resolve(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.parent.resolve().is_relative_to(self.root):
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
