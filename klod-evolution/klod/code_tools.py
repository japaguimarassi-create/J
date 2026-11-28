import ast
import json
import os
import shutil
import subprocess
import tomllib
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from .tools import MAX_TEXT_BYTES, _safe_target, analyze_file


MAX_ARCHIVE_ENTRIES = 20000
MAX_ARCHIVE_UNCOMPRESSED = 512 * 1024 * 1024


def _validate_archive(target: Path) -> dict:
    with zipfile.ZipFile(target) as archive:
        entries = archive.infolist()
        if len(entries) > MAX_ARCHIVE_ENTRIES:
            return {"valid": False, "engine": "zip-metadata", "error": "Too many archive entries"}
        total_size = sum(item.file_size for item in entries)
        if total_size > MAX_ARCHIVE_UNCOMPRESSED:
            return {"valid": False, "engine": "zip-metadata", "error": "Uncompressed archive size exceeds limit"}
        names = {item.filename for item in entries}
        return {
            "valid": True,
            "engine": "zip-metadata",
            "entries": len(entries),
            "declared_uncompressed_bytes": total_size,
            "has_manifest": "META-INF/MANIFEST.MF" in names,
            "has_android_manifest": "AndroidManifest.xml" in names,
            "has_dex": any(name.endswith(".dex") for name in names),
            "note": "Metadata only. No archive entry was extracted or executed.",
        }


def validate_code(workspace: str | Path, relative_path: str) -> dict:
    _, target = _safe_target(workspace, relative_path)
    if not target.is_file():
        raise FileNotFoundError(relative_path)

    suffix = target.suffix.lower()
    if suffix in {".jar", ".apk", ".zip"}:
        try:
            return _validate_archive(target)
        except zipfile.BadZipFile:
            return {"valid": False, "engine": "zip-metadata", "error": "Invalid ZIP archive"}

    if target.stat().st_size > MAX_TEXT_BYTES:
        raise ValueError("Text file exceeds the 2 MiB validation limit")

    content = target.read_text(encoding="utf-8")
    try:
        if suffix == ".py":
            ast.parse(content, filename=target.name)
            return {"valid": True, "engine": "python-ast", "path": relative_path}
        if suffix == ".json":
            json.loads(content)
            return {"valid": True, "engine": "json-parser", "path": relative_path}
        if suffix == ".toml":
            tomllib.loads(content)
            return {"valid": True, "engine": "toml-parser", "path": relative_path}
        if suffix in {".xml", ".svg"}:
            ElementTree.fromstring(content)
            return {"valid": True, "engine": "xml-parser", "path": relative_path}
        if suffix in {".js", ".mjs", ".cjs"}:
            node = shutil.which("node")
            if not node:
                return {
                    "valid": None,
                    "engine": "node-unavailable",
                    "path": relative_path,
                    "note": "Install Node.js to enable syntax-only validation.",
                }
            result = subprocess.run(
                [node, "--check", str(target)],
                cwd=str(Path(workspace).resolve()),
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
                env={**os.environ, "NODE_OPTIONS": ""},
            )
            return {
                "valid": result.returncode == 0,
                "engine": "node-check",
                "path": relative_path,
                "diagnostics": (result.stderr or result.stdout)[-4000:],
            }
        return {
            "valid": None,
            "engine": "unsupported",
            "path": relative_path,
            "note": "No static parser is configured for this file type.",
        }
    except (SyntaxError, ValueError, tomllib.TOMLDecodeError, ElementTree.ParseError) as exc:
        return {
            "valid": False,
            "engine": suffix.lstrip(".") + "-parser",
            "path": relative_path,
            "error": f"{type(exc).__name__}: {exc}",
        }
