import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlparse


ALLOWED_CODE_LICENSES = {
    "0BSD",
    "Apache-2.0",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "ISC",
    "MIT",
    "Unlicense",
}
ALLOWED_TEXT_LICENSES = {
    "CC0-1.0",
    "CC-BY-4.0",
    "ODC-BY-1.0",
    "Public-Domain",
}
ALLOWED_LICENSES = ALLOWED_CODE_LICENSES | ALLOWED_TEXT_LICENSES


def allowed_license(license_id: str, source_type: str) -> bool:
    license_id = (license_id or "").strip()
    source_type = (source_type or "").strip().lower()
    if source_type == "code":
        return license_id in ALLOWED_CODE_LICENSES
    if source_type == "text":
        return license_id in ALLOWED_TEXT_LICENSES
    return False


def valid_source_url(value: str) -> bool:
    parsed = urlparse(value or "")
    return (
        parsed.scheme == "https"
        and bool(parsed.hostname)
        and not parsed.username
        and not parsed.password
    )


def normalize_record(record: dict[str, Any]) -> dict[str, Any] | None:
    content = record.get("content")
    source_url = record.get("source_url", "")
    license_id = record.get("license_id", "")
    source_type = record.get("source_type", "")
    if not isinstance(content, str) or not content.strip():
        return None
    if not valid_source_url(source_url):
        return None
    if not allowed_license(license_id, source_type):
        return None
    normalized = {
        "content": content,
        "source_url": source_url,
        "license_id": license_id,
        "source_type": source_type.lower(),
        "source_name": str(record.get("source_name", "")),
        "path": str(record.get("path", "")),
        "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
    }
    return normalized


def read_licensed_jsonl(path: str | Path) -> Iterator[dict[str, Any]]:
    data_path = Path(path)
    with data_path.open("r", encoding="utf-8") as stream:
        for line_number, raw_line in enumerate(stream, start=1):
            if not raw_line.strip():
                continue
            try:
                record = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number}: {exc.msg}") from exc
            if not isinstance(record, dict):
                continue
            normalized = normalize_record(record)
            if normalized is not None:
                yield normalized


def write_jsonl(records: Iterator[dict[str, Any]], path: str | Path) -> int:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    count = 0
    file_descriptor, temporary_path = tempfile.mkstemp(
        dir=destination.parent,
        prefix=destination.name + ".",
        suffix=".tmp",
    )
    os.close(file_descriptor)
    try:
        with open(temporary_path, "w", encoding="utf-8") as stream:
            for record in records:
                normalized = normalize_record(record)
                if normalized is None or normalized["content_sha256"] in seen:
                    continue
                seen.add(normalized["content_sha256"])
                stream.write(json.dumps(normalized, ensure_ascii=False) + "\n")
                count += 1
        os.replace(temporary_path, destination)
    finally:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)
    return count
