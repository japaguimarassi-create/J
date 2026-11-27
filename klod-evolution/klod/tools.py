from pathlib import Path

MAX_TEXT_BYTES = 2 * 1024 * 1024


def _safe_target(workspace: str | Path, relative_path: str) -> tuple[Path, Path]:
    root = Path(workspace).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise PermissionError("Path escapes the authorized workspace") from exc
    return root, candidate


def analyze_file(workspace: str | Path, relative_path: str) -> dict:
    _, target = _safe_target(workspace, relative_path)
    if not target.is_file():
        raise FileNotFoundError(relative_path)
    size = target.stat().st_size
    result = {
        "path": str(target),
        "name": target.name,
        "extension": target.suffix.lower(),
        "bytes": size,
        "is_text": False,
    }
    if size > MAX_TEXT_BYTES:
        result["warning"] = "File exceeds the 2 MiB text-analysis limit"
        return result
    try:
        content = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        result["warning"] = "File is not valid UTF-8 text"
        return result
    result.update({
        "is_text": True,
        "characters": len(content),
        "lines": len(content.splitlines()),
        "content": content,
    })
    return result


def create_file(workspace: str | Path, relative_path: str, content: str, overwrite: bool = False) -> dict:
    _, target = _safe_target(workspace, relative_path)
    encoded = content.encode("utf-8")
    if len(encoded) > MAX_TEXT_BYTES:
        raise ValueError("Content exceeds the 2 MiB file-creation limit")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not overwrite:
        raise FileExistsError(relative_path)
    target.write_bytes(encoded)
    return {"path": str(target), "bytes": len(encoded), "created": True}
