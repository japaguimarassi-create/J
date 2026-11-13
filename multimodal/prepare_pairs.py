from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ALLOWED = {"CC0-1.0", "CC-BY-4.0"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".gif"}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
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


def safe_name(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-.")[:100] or "asset"


def caption_for(row: dict[str, Any]) -> str:
    parts = [str(row.get("title", "")).strip(), str(row.get("description", "")).strip()]
    tags = row.get("tags", [])
    if isinstance(tags, list):
        parts.extend(str(tag).strip() for tag in tags[:20])
    elif tags:
        parts.append(str(tags))
    text = ". ".join(part for part in parts if part)
    return " ".join(text.split())[:1500]


def image_is_valid(path: Path) -> bool:
    try:
        from PIL import Image
        with Image.open(path) as image:
            image.verify()
        return True
    except Exception:
        return False


def video_duration(path: Path) -> float:
    command = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
    if result.returncode != 0:
        return 0.0
    try:
        return max(0.0, float(result.stdout.strip()))
    except ValueError:
        return 0.0


def sample_video(path: Path, asset_id: str, frames_dir: Path, count: int) -> list[Path]:
    duration = video_duration(path)
    if duration <= 0:
        raise RuntimeError("ffprobe could not read video duration")
    output_dir = frames_dir / safe_name(asset_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for index in range(count):
        timestamp = min(max(0.0, duration - 0.05), duration * (index + 0.5) / count)
        target = output_dir / ("frame_" + str(index).zfill(3) + ".jpg")
        if not target.exists() or target.stat().st_size == 0:
            command = [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                "-ss", format(timestamp, ".3f"), "-i", str(path), "-frames:v", "1",
                "-vf", "scale=768:768:force_original_aspect_ratio=decrease",
                "-q:v", "3", str(target),
            ]
            result = subprocess.run(command, capture_output=True, text=True, timeout=120, check=False)
            if result.returncode != 0:
                target.unlink(missing_ok=True)
                continue
        if target.is_file() and target.stat().st_size > 0 and image_is_valid(target):
            outputs.append(target)
    return outputs


def add_pair(pairs: list[dict[str, Any]], row: dict[str, Any], image_path: Path, caption: str) -> None:
    pairs.append({
        "image_path": str(image_path.resolve()),
        "text": caption,
        "asset_id": str(row.get("asset_id", "")),
        "media_type": str(row.get("media_type", "image")),
        "source": str(row.get("source", "")),
        "source_url": str(row.get("source_url", "")),
        "license": str(row.get("license", "")),
        "license_url": str(row.get("license_url", "")),
        "attribution": str(row.get("attribution", "")),
        "rights_verified": True,
    })


def main() -> None:
    parser = argparse.ArgumentParser(description="Build image-caption pairs from verified image, video and 3D media.")
    parser.add_argument("--manifest", type=Path, default=Path("datasets/assets.jsonl"))
    parser.add_argument("--out", type=Path, default=Path("datasets/pairs.jsonl"))
    parser.add_argument("--frames-dir", type=Path, default=Path("datasets/frames"))
    parser.add_argument("--preview-dir", type=Path, default=Path("datasets/previews"))
    parser.add_argument("--frames-per-video", type=int, default=4)
    parser.add_argument("--limit", type=int, default=0, help="0 means no asset-count limit")
    args = parser.parse_args()
    if args.frames_per_video < 1 or args.frames_per_video > 16 or args.limit < 0:
        raise ValueError("frames-per-video must be 1-16 and limit must be >= 0")
    rows = read_jsonl(args.manifest)
    pairs: list[dict[str, Any]] = []
    stats = {"assets_seen": 0, "images": 0, "video_frames": 0, "rendered_3d_views": 0, "skipped": 0}
    for row in rows:
        if args.limit and stats["assets_seen"] >= args.limit:
            break
        stats["assets_seen"] += 1
        if row.get("rights_verified") is not True or row.get("license") not in ALLOWED:
            stats["skipped"] += 1
            continue
        asset_id = str(row.get("asset_id", ""))
        caption = caption_for(row)
        source_path = Path(str(row.get("local_path", ""))).expanduser()
        if not asset_id or not caption or not source_path.is_file():
            stats["skipped"] += 1
            continue
        media = str(row.get("media_type", ""))
        if media == "image":
            if source_path.suffix.lower() in IMAGE_EXTENSIONS and image_is_valid(source_path):
                add_pair(pairs, row, source_path, caption)
                stats["images"] += 1
        elif media == "video":
            try:
                frames = sample_video(source_path, asset_id, args.frames_dir, args.frames_per_video)
                for frame in frames:
                    add_pair(pairs, row, frame, caption)
                stats["video_frames"] += len(frames)
                if not frames:
                    stats["skipped"] += 1
            except Exception as exc:
                print("video skipped " + asset_id + ": " + str(exc))
                stats["skipped"] += 1
        elif media == "3d":
            previews = sorted(args.preview_dir.glob(safe_name(asset_id) + "_v*.png"))
            valid = [path for path in previews if image_is_valid(path)]
            for preview in valid:
                add_pair(pairs, row, preview, caption)
            stats["rendered_3d_views"] += len(valid)
            if not valid:
                stats["skipped"] += 1
        else:
            stats["skipped"] += 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as handle:
        for row in pairs:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    stats["training_pairs"] = len(pairs)
    stats["output"] = str(args.out.resolve())
    print(json.dumps(stats, ensure_ascii=False))


if __name__ == "__main__":
    main()
