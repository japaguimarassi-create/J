from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from PIL import Image

ALLOWED = {"CC0-1.0", "CC-BY-4.0"}
BLOCKED_SOURCES = {"hunyuan3d", "hunyuan3d_2.1", "tencent_hunyuan3d"}


def read_rows(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(str(path) + ":" + str(number) + ": invalid JSON") from exc
            if isinstance(row, dict):
                rows.append(row)
    return rows


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prepare(args: argparse.Namespace) -> dict[str, Any]:
    rows = read_rows(args.pairs)
    images_dir = args.output / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = args.output / "metadata.jsonl"
    existing = set()
    total_bytes = 0
    copied = 0
    rejected = {"rights": 0, "source_policy": 0, "missing": 0, "corrupt": 0, "duplicate": 0}
    metadata: list[dict[str, Any]] = []
    seen_hashes: set[str] = set()
    max_bytes = int(args.max_total_gb * 1024**3)
    for row in rows:
        if copied >= args.max_items or total_bytes >= max_bytes:
            break
        if row.get("rights_verified") is not True or row.get("license") not in ALLOWED:
            rejected["rights"] += 1
            continue
        source = str(row.get("source", "")).casefold()
        if any(name in source for name in BLOCKED_SOURCES) or row.get("training_allowed") is False:
            rejected["source_policy"] += 1
            continue
        original = Path(str(row.get("image_path", ""))).expanduser()
        caption = " ".join(str(row.get("text", "")).split())[:1500]
        if not original.is_file() or not caption:
            rejected["missing"] += 1
            continue
        try:
            with Image.open(original) as image:
                image.verify()
        except Exception:
            rejected["corrupt"] += 1
            continue
        digest = str(row.get("sha256") or "") or sha256(original)
        if digest in seen_hashes:
            rejected["duplicate"] += 1
            continue
        size = original.stat().st_size
        if size <= 0 or total_bytes + size > max_bytes:
            break
        extension = original.suffix.lower()
        if extension not in {".jpg", ".jpeg", ".png", ".webp"}:
            rejected["corrupt"] += 1
            continue
        asset_id = str(row.get("asset_id") or "asset-" + digest[:16])
        safe_id = "".join(char if char.isalnum() or char in "-_." else "-" for char in asset_id)[:100]
        filename = safe_id + extension
        target = images_dir / filename
        if target.exists():
            filename = safe_id + "-" + digest[:10] + extension
            target = images_dir / filename
        shutil.copy2(original, target)
        record = {
            "file_name": "images/" + filename,
            "text": caption,
            "asset_id": asset_id,
            "license": row["license"],
            "license_url": str(row.get("license_url", "")),
            "source_url": str(row.get("source_url", "")),
            "attribution": str(row.get("attribution", "")),
            "media_type": str(row.get("media_type", "image")),
            "sha256": digest,
        }
        metadata.append(record)
        seen_hashes.add(digest)
        copied += 1
        total_bytes += size
    if copied < 10:
        raise ValueError("At least 10 unique, licensed image-caption pairs are required for LoRA training; accepted " + str(copied))
    with metadata_path.open("w", encoding="utf-8") as handle:
        for record in metadata:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    report = {
        "accepted": copied,
        "rejected": rejected,
        "total_gb": round(total_bytes / 1024**3, 4),
        "output": str(args.output.resolve()),
        "metadata": str(metadata_path.resolve()),
        "license_counts": {
            license_name: sum(1 for row in metadata if row["license"] == license_name)
            for license_name in sorted(ALLOWED)
        },
    }
    (args.output / "dataset_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare a Hugging Face imagefolder dataset for SDXL LoRA training.")
    parser.add_argument("--pairs", type=Path, default=Path("datasets/pairs.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("datasets/sdxl_lora"))
    parser.add_argument("--max-items", type=int, default=5000)
    parser.add_argument("--max-total-gb", type=float, default=20)
    args = parser.parse_args()
    if args.max_items < 10 or args.max_items > 100000 or args.max_total_gb <= 0:
        raise ValueError("max-items must be 10-100000 and max-total-gb must be positive.")
    print(json.dumps(prepare(args), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
