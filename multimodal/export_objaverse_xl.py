from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path
from typing import Any

ALLOWED = {"cc0", "cc0-1.0", "public domain", "by", "cc-by", "cc-by-4.0"}


def canonical_license(raw: Any) -> str:
    value = str(raw or "").strip().casefold().replace("_", "-")
    value = " ".join(value.split())
    compact = value.replace(" ", "")
    if compact in {"cc0", "cc0-1.0", "cczero"}:
        return "CC0-1.0"
    if compact in {"by", "cc-by", "cc-by-4.0", "ccby", "ccby4.0"}:
        return "CC-BY-4.0"
    if "nc" in compact:
        return "CC-BY-NC-OR-RESTRICTED"
    if "sa" in compact:
        return "CC-BY-SA-OR-RESTRICTED"
    if "nd" in compact:
        return "CC-BY-ND-OR-RESTRICTED"
    return str(raw or "unknown")


def json_safe(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            return str(value)
    return str(value)


def add_records(records: list[dict[str, Any]], manifest: Path) -> None:
    manifest.parent.mkdir(parents=True, exist_ok=True)
    existing: set[str] = set()
    if manifest.exists():
        with manifest.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    existing.add(str(json.loads(line).get("asset_id", "")))
                except Exception:
                    continue
    with manifest.open("a", encoding="utf-8") as handle:
        for row in records:
            if row["asset_id"] not in existing:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                existing.add(row["asset_id"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Download a rights-filtered sample of Objaverse-XL 3D models.")
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--seed", type=int, default=20261113)
    parser.add_argument("--download-dir", type=Path, default=Path("datasets/raw/objaverse_xl"))
    parser.add_argument("--metadata-dir", type=Path, default=Path("datasets/objaverse_metadata"))
    parser.add_argument("--manifest", type=Path, default=Path("datasets/assets.jsonl"))
    args = parser.parse_args()
    if args.limit < 1 or args.limit > 100000 or args.workers < 1 or args.workers > 8:
        raise ValueError("limit must be 1-100000 and workers must be 1-8.")
    try:
        import objaverse.xl as oxl
    except ImportError as exc:
        raise SystemExit("Install the optional dependency first: python -m pip install objaverse") from exc

    download_dir = args.download_dir.resolve()
    metadata_dir = args.metadata_dir.resolve()
    download_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)
    print("Loading Objaverse-XL item metadata. The initial metadata pass can be large.")
    table = oxl.get_annotations(download_dir=str(metadata_dir), refresh=False)
    required = {"fileIdentifier", "license", "fileType"}
    missing = required.difference(set(table.columns))
    if missing:
        raise RuntimeError("Objaverse-XL metadata schema changed; missing columns: " + ", ".join(sorted(missing)))
    eligible = table[table["license"].map(lambda value: str(value or "").strip().casefold().replace("_", "-") in ALLOWED)].copy()
    if eligible.empty:
        raise RuntimeError("No records matched the conservative CC0/CC-BY filter. Inspect the current metadata before changing policy.")
    chosen = eligible.sample(n=min(args.limit, len(eligible)), random_state=args.seed)
    print("Eligible items: " + str(len(eligible)) + "; selected: " + str(len(chosen)))
    paths = oxl.download_objects(objects=chosen, download_dir=str(download_dir), processes=args.workers)
    records: list[dict[str, Any]] = []
    for _, row in chosen.iterrows():
        uid = str(row["fileIdentifier"])
        local_path = paths.get(uid)
        if not local_path:
            print("missing " + uid)
            continue
        path = Path(str(local_path)).expanduser()
        if not path.exists() or not path.is_file():
            print("not found " + uid + " " + str(path))
            continue
        raw_license = str(row["license"])
        license_value = canonical_license(raw_license)
        if license_value not in {"CC0-1.0", "CC-BY-4.0"}:
            continue
        metadata = row.get("metadata", {})
        if not isinstance(metadata, dict):
            try:
                metadata = json.loads(metadata) if isinstance(metadata, str) else {}
            except json.JSONDecodeError:
                metadata = {}
        title = str(metadata.get("name") or metadata.get("title") or uid)
        description = str(metadata.get("description") or metadata.get("caption") or "")
        tags = metadata.get("tags", metadata.get("categories", []))
        if not isinstance(tags, list):
            tags = [str(tags)] if tags else []
        digest = str(row.get("sha256") or "")
        if not digest:
            hasher = hashlib.sha256()
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    hasher.update(chunk)
            digest = hasher.hexdigest()
        records.append({
            "asset_id": "objaverse-xl-" + uid,
            "source": "objaverse_xl",
            "media_type": "3d",
            "title": title[:300],
            "description": description[:2000],
            "tags": [str(tag)[:100] for tag in tags[:30]],
            "license": license_value,
            "license_source_value": raw_license,
            "license_url": "https://creativecommons.org/licenses/by/4.0/" if license_value == "CC-BY-4.0" else "https://creativecommons.org/publicdomain/zero/1.0/",
            "attribution": "Objaverse-XL asset " + uid + "; retain original creator attribution from item metadata",
            "source_url": "https://objaverse.allenai.org/docs/intro/",
            "local_path": str(path.resolve()),
            "rights_verified": True,
            "license_review": "item_metadata_allowlisted",
            "source_repository": str(row.get("source", "")),
            "file_type": str(row.get("fileType", "")),
            "sha256": digest,
            "metadata": json_safe(metadata),
        })
    add_records(records, args.manifest.resolve())
    print(json.dumps({
        "eligible_in_metadata": int(len(eligible)),
        "selected": int(len(chosen)),
        "downloaded_and_registered": len(records),
        "manifest": str(args.manifest.resolve()),
        "noncommercial_and_unknown_items_excluded": True,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
