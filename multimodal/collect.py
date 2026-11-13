from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {"CC0-1.0", "CC-BY-4.0"}
EXTENSIONS = {
    "image": {".jpg", ".jpeg", ".png", ".webp", ".gif", ".tif", ".tiff"},
    "video": {".mp4", ".webm", ".ogv", ".mov", ".m4v"},
    "3d": {".glb", ".obj", ".fbx", ".stl"},
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(str(path) + ":" + str(number) + ": invalid JSON") from exc
            if not isinstance(item, dict):
                raise ValueError(str(path) + ":" + str(number) + ": each record must be an object")
            rows.append(item)
    return rows


def safe_name(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-.")
    return value[:120] or "asset"


def valid_url(value: str) -> bool:
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname:
        return False
    host = parsed.hostname.lower()
    if host in {"localhost", "127.0.0.1", "::1"} or host.endswith(".local"):
        return False
    return True


def existing_ids(path: Path) -> set[str]:
    found: set[str] = set()
    if not path.exists():
        return found
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                found.add(str(json.loads(line).get("asset_id", "")))
            except Exception:
                continue
    return found


def download_one(record: dict[str, Any], root: Path, max_file_bytes: int, timeout: int) -> dict[str, Any] | None:
    asset_id = str(record.get("asset_id", "")).strip()
    media = str(record.get("media_type", "")).lower()
    license_name = str(record.get("license", "unknown")).upper()
    url = str(record.get("download_url", "")).strip()
    if not asset_id or media not in EXTENSIONS:
        return None
    if record.get("rights_verified") is not True or license_name not in ALLOWED:
        return None
    if not valid_url(url):
        return None
    extension = Path(urllib.parse.urlparse(url).path).suffix.lower()
    if extension not in EXTENSIONS[media]:
        return None
    target_dir = root / "raw" / media
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / (safe_name(asset_id) + extension)
    if target.exists() and target.stat().st_size > 0:
        digest = hashlib.sha256()
        with target.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        updated = dict(record)
        updated["local_path"] = str(target.resolve())
        updated["sha256"] = digest.hexdigest()
        return updated
    temporary = target.with_suffix(target.suffix + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": "MotionForgeMultimodal/1.0", "Accept": "*/*"})
    digest = hashlib.sha256()
    total = 0
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response, temporary.open("wb") as output:
            final_url = response.geturl()
            if not valid_url(final_url):
                raise ValueError("redirected to a non-HTTPS or local URL")
            announced = response.headers.get("Content-Length")
            if announced and int(announced) > max_file_bytes:
                raise ValueError("file exceeds per-file size cap")
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_file_bytes:
                    raise ValueError("file exceeds per-file size cap")
                output.write(chunk)
                digest.update(chunk)
        if total == 0:
            raise ValueError("empty download")
        temporary.replace(target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    updated = dict(record)
    updated["local_path"] = str(target.resolve())
    updated["sha256"] = digest.hexdigest()
    updated["downloaded_bytes"] = total
    updated["download_url"] = url
    return updated


def main() -> None:
    parser = argparse.ArgumentParser(description="Download only verified, allowlisted media records.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out-root", type=Path, default=Path("datasets"))
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--max-total-gb", type=float, default=5.0)
    parser.add_argument("--max-file-mb", type=float, default=200.0)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.limit < 1 or args.limit > 100000 or args.max_total_gb <= 0 or args.max_file_mb <= 0:
        raise ValueError("Invalid download limits.")
    rows = read_jsonl(args.manifest)
    root = args.out_root.resolve()
    output_manifest = root / "assets.jsonl"
    seen = existing_ids(output_manifest)
    total_cap = int(args.max_total_gb * 1024**3)
    file_cap = int(args.max_file_mb * 1024**2)
    downloaded_total = 0
    eligible = 0
    downloaded = 0
    skipped = 0
    errors = 0
    root.mkdir(parents=True, exist_ok=True)
    for record in rows:
        if eligible >= args.limit:
            break
        asset_id = str(record.get("asset_id", ""))
        if not asset_id or asset_id in seen:
            skipped += 1
            continue
        if record.get("rights_verified") is not True or str(record.get("license", "")).upper() not in ALLOWED:
            skipped += 1
            continue
        eligible += 1
        if args.dry_run:
            print("approved " + asset_id + " " + str(record.get("license")))
            continue
        if downloaded_total >= total_cap:
            print("Stopped: total storage cap reached.")
            break
        try:
            updated = download_one(record, root, min(file_cap, total_cap - downloaded_total), args.timeout)
            if updated is None:
                skipped += 1
                continue
            size = int(updated.get("downloaded_bytes", 0))
            downloaded_total += size
            with output_manifest.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(updated, ensure_ascii=False) + "\n")
            seen.add(asset_id)
            downloaded += 1
            print("downloaded " + asset_id + " bytes=" + str(size))
        except Exception as exc:
            errors += 1
            print("failed " + asset_id + ": " + str(exc))
    summary = {
        "manifest_records": len(rows),
        "eligible_checked": eligible,
        "downloaded": downloaded,
        "skipped": skipped,
        "errors": errors,
        "downloaded_gb_this_run": round(downloaded_total / 1024**3, 4),
        "assets_manifest": str(output_manifest),
        "dry_run": args.dry_run,
    }
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
