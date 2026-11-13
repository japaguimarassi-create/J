from __future__ import annotations

import argparse
import html
import json
import os
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

API = "https://api.si.edu/openaccess/api/v1.0/search"
CC0_URL = "https://creativecommons.org/publicdomain/zero/1.0/"


def plain(value: Any) -> str:
    raw = str(value or "")
    raw = re.sub(r"<[^>]*>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(raw)).strip()


def api_get(params: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        API + "?" + urllib.parse.urlencode(params),
        headers={"User-Agent": "MotionForgeMultimodal/1.0", "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        if response.status != 200:
            raise RuntimeError("Smithsonian API returned HTTP " + str(response.status))
        payload = json.loads(response.read(12_000_000).decode("utf-8"))
    if "response" not in payload:
        raise RuntimeError("Unexpected Smithsonian API response.")
    return payload


def first_text(value: Any) -> str:
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                candidate = plain(item.get("content") or item.get("text") or item.get("label"))
                if candidate:
                    return candidate
            elif item:
                return plain(item)
    if isinstance(value, dict):
        return plain(value.get("content") or value.get("text") or value.get("label"))
    return plain(value)


def media_records(record: dict[str, Any]) -> list[dict[str, Any]]:
    content = record.get("content") or {}
    description = content.get("descriptiveNonRepeating") or {}
    online = description.get("online_media") or {}
    media = online.get("media", []) if isinstance(online, dict) else []
    return media if isinstance(media, list) else []


def select_download(media: dict[str, Any]) -> str:
    resources = media.get("resources") or []
    if isinstance(resources, list):
        preferred = sorted(
            [item for item in resources if isinstance(item, dict)],
            key=lambda item: (
                0 if "high-resolution jpeg" in str(item.get("label", "")).casefold() else
                1 if "high-resolution" in str(item.get("label", "")).casefold() else
                2 if "download" in str(item.get("label", "")).casefold() else 3
            ),
        )
        for item in preferred:
            url = str(item.get("url", ""))
            if url.startswith("https://"):
                return url
    for key in ("content", "thumbnail"):
        url = str(media.get(key, ""))
        if url.startswith("https://"):
            return url
    return ""


def export(query: str, limit: int, rows_per_page: int, output: Path, api_key: str) -> dict[str, int]:
    if not api_key:
        raise SystemExit("Set SMITHSONIAN_API_KEY in the environment. Never put the key in Git.")
    if limit < 1 or limit > 1_000_000 or rows_per_page < 1 or rows_per_page > 100:
        raise ValueError("limit must be 1-1000000 and rows-per-page 1-100.")
    search_query = "online_media_type:Images"
    if query.strip():
        search_query += " AND (" + query.strip() + ")"
    output.parent.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    if output.exists():
        with output.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    seen.add(str(json.loads(line).get("asset_id", "")))
                except Exception:
                    continue
    exported = 0
    cc0 = 0
    start = 0
    while exported < limit:
        payload = api_get({
            "q": search_query,
            "api_key": api_key,
            "start": start,
            "rows": min(rows_per_page, limit - exported),
            "sort": "id",
        })
        response = payload.get("response") or {}
        objects = response.get("rows") or []
        if not objects:
            break
        batch: list[dict[str, Any]] = []
        for record in objects:
            content = record.get("content") or {}
            descriptive = content.get("descriptiveNonRepeating") or {}
            record_id = str(descriptive.get("record_ID") or record.get("id") or "")
            title = first_text((content.get("freetext") or {}).get("title")) or record_id
            description = first_text((content.get("freetext") or {}).get("notes"))
            source_page = str(descriptive.get("guid") or "https://www.si.edu/openaccess")
            for media in media_records(record):
                usage = media.get("usage") or {}
                access = str(usage.get("access", "")).strip().upper()
                if access != "CC0":
                    continue
                download_url = select_download(media)
                if not download_url:
                    continue
                media_id = str(media.get("idsId") or media.get("id") or record_id)
                asset_id = "smithsonian-" + re.sub(r"[^a-zA-Z0-9._-]+", "-", media_id)[:120]
                if asset_id in seen:
                    continue
                label = str(media.get("type", "")).casefold()
                media_kind = "3d" if any(ext in label for ext in ("3d", "model")) else "image"
                attribution = first_text((content.get("freetext") or {}).get("creditLine"))
                batch.append({
                    "asset_id": asset_id,
                    "source": "smithsonian_open_access",
                    "media_type": media_kind,
                    "title": title[:300],
                    "description": (description or first_text(media.get("altTextAccessibility")))[:2000],
                    "tags": [],
                    "license": "CC0-1.0",
                    "license_url": CC0_URL,
                    "attribution": attribution[:1000],
                    "source_url": source_page,
                    "download_url": download_url,
                    "local_path": "",
                    "rights_verified": True,
                    "license_review": "media_usage_access_is_CC0",
                    "media_id": media_id,
                    "mime_type": str(media.get("type", "")),
                    "sha256": "",
                })
                seen.add(asset_id)
                cc0 += 1
                if exported + len(batch) >= limit:
                    break
            if exported + len(batch) >= limit:
                break
        if batch:
            with output.open("a", encoding="utf-8") as handle:
                for item in batch:
                    handle.write(json.dumps(item, ensure_ascii=False) + "\n")
                    exported += 1
        start += len(objects)
        total = int(response.get("rowCount") or response.get("rows") or 0)
        if len(objects) < rows_per_page or (total and start >= total):
            break
        time.sleep(0.15)
    return {"exported_cc0_media": exported, "api_rows_scanned": start, "manifest": str(output.resolve())}


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Smithsonian Open Access records with per-media CC0 verification.")
    parser.add_argument("--query", default="")
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--rows-per-page", type=int, default=100)
    parser.add_argument("--out", type=Path, default=Path("datasets/smithsonian_manifest.jsonl"))
    parser.add_argument("--api-key", default=os.environ.get("SMITHSONIAN_API_KEY", ""))
    args = parser.parse_args()
    result = export(args.query, args.limit, args.rows_per_page, args.out, args.api_key)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
