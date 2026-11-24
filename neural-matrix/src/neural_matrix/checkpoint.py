import json
import os
from pathlib import Path
import tempfile
from typing import Any


def _reject_constant(value: str):
    raise ValueError(f"Checkpoint contains non-finite JSON constant: {value}")


def read_checkpoint(path: str | Path) -> dict[str, Any]:
    checkpoint_path = Path(path)
    try:
        with checkpoint_path.open("r", encoding="utf-8") as stream:
            payload = json.load(stream, parse_constant=_reject_constant)
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid checkpoint JSON: {error.msg}") from error
    if not isinstance(payload, dict):
        raise ValueError("Checkpoint root must be a JSON object")
    marker = payload.get("format")
    if marker not in (None, "neural-matrix"):
        raise ValueError("File is not a Neural Matrix checkpoint")
    return payload


def write_checkpoint(path: str | Path, payload: dict[str, Any]) -> None:
    checkpoint_path = Path(path)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    state = dict(payload)
    state.setdefault("format", "neural-matrix")
    descriptor, temporary = tempfile.mkstemp(prefix=checkpoint_path.name, dir=checkpoint_path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(state, stream, separators=(",", ":"), allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, checkpoint_path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
