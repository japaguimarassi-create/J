from __future__ import annotations

import argparse
import html
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

API = "https://commons.wikimedia.org/w/api.php"
ALLOWED = {"CC0-1.0", "CC-BY-4.0"}


def api_get(params: dict[str, Any]) -> dict[str, Any]:
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(
        API + "?" + query,
        headers={"User-Agent": "MotionForgeMultimodal/1.0 (rights-aware dataset indexer)", "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError("Wikimedia API returned HTTP " + str(response.status))
        payload = json.loads(response.read(8_000_000).decode("utf-8"))
    if "error" in payload:
        raise RuntimeError("Wikimedia API error: " + str(payload["error"]))
    return payload


def plain(value: Any) -> str:
    raw = str(value or "")
    raw = re.sub(r"<[^>]*>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(raw)).strip()


def license_name(raw: str) -> str:
    value = plain(raw).casefold()
    value = value.replace("creative commons", "").strip()
    value = re.sub(r"\s+", " ", value)
    if "cc0" in value:
        return "CC0-1.0"
    if re.search(r"\bcc\s*by\s*4\.0\b", value):
        return "CC-BY-4.0"
    if re.search(r"\bcc\s*by\s*sa\s*4\.0\b", value):
        return "CC-BY-SA-4.0"
    if "public domain" in value:
        return "Public Domain"
    return plain(raw) or "unknown"


def first_text(metadata: dict[str, Any], key: str) -> str:
    item = metadata.get(key)
    if isinstance(item, dict):
        return plain(item.get("value", ""))
    return plain(item)


def export(media: str, query: str, limit: int, output: Path) -> dict[str, int]:
    if media not in {"image", "video"}:
        raise ValueError("media must be image or video")
    if limit < 1 or limit > 50000:
        raise ValueError("limit must be between 1 and 50000")
    search = "filetype:bitmap" if media == "image" else "filetype:video"
    if query.strip():
        search += " " + query.strip()
    output.parent.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    if output.exists():
        with output.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    item = json.loads(line)
                    seen.add(str(item.get("asset_id", "")))
                except json.JSONDecodeError:
                    continue
    written = 0
    approved = 0
    continuation: dict[str, Any] = {}
    while written < limit:
        params: dict[str, Any] = {
            "action": "query",
            "format": "json",
            "formatversion": 2,
            "generator": "search",
            "gsrsearch": search,
            "gsrnamespace": 6,
            "gsrlimit": min(50, limit - written),
            "prop": "imageinfo",
            "iiprop": "url|mime|extmetadata",
            "iiurlwidth": 800,
        }
        params.update(continuation)
        payload = api_get(params)
        pages = payload.get("query", {}).get("pages", [])
        if isinstance(pages, dict):
            pages = list(pages.values())
        batch: list[dict[str, Any]] = []
        for page in pages:
            imageinfo = page.get("imageinfo") or []
            if not imageinfo:
                continue
            info = imageinfo[0]
            mime = str(info.get("mime", "")).lower()
            detected = "video" if mime.startswith("video/") else "image" if mime.startswith("image/") else ""
            if detected != media:
                continue
            ext = info.get("extmetadata") or {}
            short_name = first_text(ext, "LicenseShortName")
            normalized = license_name(short_name)
            title = plain(page.get("title", ""))
            page_id = str(page.get("pageid", ""))
            file_url = str(info.get("url", ""))
            if not title or not page_id or not file_url.startswith("https://"):
                continue
            asset_id = "commons-" + page_id
            if asset_id in seen:
                continue
            source_page = "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"), safe=":/()")
            artist = first_text(ext, "Artist")
            credit = first_text(ext, "Credit")
            description = first_text(ext, "ImageDescription")
            attribution = "; ".join(part for part in [artist, credit] if part)
            record = {
                "asset_id": asset_id,
                "source": "wikimedia_commons",
                "media_type": media,
                "title": title.removeprefix("File:"),
                "description": description[:2000],
                "tags": [],
                "license": normalized,
                "license_url": first_text(ext, "LicenseUrl"),
                "attribution": attribution[:1000],
                "source_url": source_page,
                "download_url": file_url,
                "local_path": "",
                "rights_verified": normalized in ALLOWED,
                "license_review": "approved_by_default_policy" if normalized in ALLOWED else "manual_review_required",
                "mime_type": mime,
                "sha256": "",
            }
            batch.append(record)
            seen.add(asset_id)
            if len(batch) + written >= limit:
                break
        if batch:
            with output.open("a", encoding="utf-8") as handle:
                for record in batch:
                    handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                    written += 1
                    approved += int(record["rights_verified"])
        continuation = payload.get("continue") or {}
        if not continuation or not pages:
            break
        time.sleep(0.15)
    return {"exported": written, "approved_by_default_policy": approved, "requires_manual_review": written - approved}


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Wikimedia Commons files with their item-level license metadata.")
    parser.add_argument("--media", choices=["image", "video"], required=True)
    parser.add_argument("--query", default="")
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--out", type=Path, default=Path("datasets/wikimedia_manifest.jsonl"))
    args = parser.parse_args()
    result = export(args.media, args.query, args.limit, args.out)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
