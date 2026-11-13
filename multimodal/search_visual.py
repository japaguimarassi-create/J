from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image

from train_visual import ProjectionHead


def load_pairs(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("rights_verified") is True and row.get("license") in {"CC0-1.0", "CC-BY-4.0"}:
                image_path = Path(str(row.get("image_path", "")))
                if image_path.is_file() and row.get("text"):
                    rows.append(row)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Find local visual assets matching a text description.")
    parser.add_argument("--pairs", type=Path, default=Path("datasets/pairs.jsonl"))
    parser.add_argument("--checkpoint", type=Path, default=Path("artifacts/multimodal/visual_adapter.pt"))
    parser.add_argument("--query", required=True)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    if args.top_k < 1 or args.top_k > 100 or args.batch_size < 1 or args.batch_size > 128 or args.limit < 0:
        raise ValueError("Invalid top-k, batch-size or limit.")
    if not args.checkpoint.is_file():
        raise FileNotFoundError("Checkpoint not found: " + str(args.checkpoint))
    saved = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    try:
        import open_clip
    except ImportError as exc:
        raise SystemExit("Install multimodal dependencies: python -m pip install -r multimodal/requirements.txt") from exc
    model_name = str(saved["backbone"])
    pretrained = str(saved["pretrained"])
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    backbone, _, preprocess = open_clip.create_model_and_transforms(model_name, pretrained=pretrained)
    tokenizer = open_clip.get_tokenizer(model_name)
    backbone.to(device).eval()
    for parameter in backbone.parameters():
        parameter.requires_grad_(False)
    image_dim = int(backbone.visual.output_dim)
    text_dim = int(backbone.text_projection.shape[-1])
    image_projector = ProjectionHead(image_dim).to(device)
    text_projector = ProjectionHead(text_dim).to(device)
    image_projector.load_state_dict(saved["image_projector"])
    text_projector.load_state_dict(saved["text_projector"])
    image_projector.eval()
    text_projector.eval()
    with torch.no_grad():
        tokens = tokenizer([args.query]).to(device)
        query_vector = text_projector(backbone.encode_text(tokens).float())
    rows = load_pairs(args.pairs)
    if args.limit:
        rows = rows[:args.limit]
    top: list[tuple[float, dict[str, Any]]] = []
    valid_count = 0
    with torch.no_grad():
        for start in range(0, len(rows), args.batch_size):
            batch_rows = rows[start:start + args.batch_size]
            images: list[torch.Tensor] = []
            valid_rows: list[dict[str, Any]] = []
            for row in batch_rows:
                try:
                    with Image.open(row["image_path"]) as source:
                        images.append(preprocess(source.convert("RGB")))
                    valid_rows.append(row)
                except Exception:
                    continue
            if not images:
                continue
            vectors = image_projector(backbone.encode_image(torch.stack(images).to(device)).float())
            scores = (vectors @ query_vector.T).flatten().cpu().tolist()
            valid_count += len(scores)
            for score, row in zip(scores, valid_rows):
                top.append((float(score), row))
            top.sort(key=lambda item: item[0], reverse=True)
            top = top[:args.top_k]
    results = []
    for score, row in top:
        results.append({
            "similarity": round(score, 5),
            "asset_id": row.get("asset_id"),
            "media_type": row.get("media_type"),
            "source": row.get("source"),
            "source_url": row.get("source_url"),
            "license": row.get("license"),
            "attribution": row.get("attribution"),
            "image_path": row.get("image_path"),
            "description": row.get("text"),
        })
    print(json.dumps({
        "query": args.query,
        "candidates_scanned": valid_count,
        "results": results,
        "note": "Similarity is a retrieval score, not a factual confidence value.",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
