from __future__ import annotations

import argparse
import json
import math
import random
import time
from collections import Counter
from pathlib import Path
from typing import Any

import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
from torch.utils.data import DataLoader, Dataset

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {"CC0-1.0", "CC-BY-4.0"}


class PairDataset(Dataset):
    def __init__(self, rows: list[dict[str, Any]], transform: Any) -> None:
        self.rows = rows
        self.transform = transform

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, str]:
        row = self.rows[index]
        path = Path(row["image_path"])
        with Image.open(path) as source:
            image = source.convert("RGB")
            tensor = self.transform(image)
        return tensor, str(row["text"])


class ProjectionHead(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int = 256, output_dim: int = 128) -> None:
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, output_dim),
        )

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        return F.normalize(self.layers(value.float()), dim=-1)


def load_rows(path: Path) -> tuple[list[dict[str, Any]], Counter[str]]:
    rows: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    with path.open("r", encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(str(path) + ":" + str(number) + ": invalid JSON") from exc
            if not isinstance(row, dict):
                counts["invalid_record"] += 1
                continue
            license_value = str(row.get("license", ""))
            if row.get("rights_verified") is not True or license_value not in ALLOWED:
                counts["rights_rejected"] += 1
                continue
            image_path = Path(str(row.get("image_path", ""))).expanduser()
            text = str(row.get("text", "")).strip()
            asset_id = str(row.get("asset_id", "")).strip()
            if not image_path.is_file() or not text or not asset_id:
                counts["missing_file_or_caption"] += 1
                continue
            try:
                with Image.open(image_path) as image:
                    image.verify()
            except Exception:
                counts["corrupt_image"] += 1
                continue
            normalized = dict(row)
            normalized["image_path"] = str(image_path.resolve())
            normalized["text"] = " ".join(text.split())[:1500]
            rows.append(normalized)
            counts["accepted_" + license_value] += 1
    if len(rows) < 5:
        raise ValueError("At least 5 valid, license-approved image-caption pairs are required. Accepted: " + str(len(rows)))
    return rows, counts


def split_by_asset(rows: list[dict[str, Any]], seed: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(str(row["asset_id"]), []).append(row)
    keys = list(groups)
    random.Random(seed).shuffle(keys)
    if len(keys) >= 5:
        validation_count = max(1, min(len(keys) - 2, round(len(keys) * 0.1)))
        validation_keys = set(keys[:validation_count])
        train = [row for key, items in groups.items() if key not in validation_keys for row in items]
        validation = [row for key, items in groups.items() if key in validation_keys for row in items]
        return train, validation
    shuffled = list(rows)
    random.Random(seed).shuffle(shuffled)
    validation_count = max(1, min(len(shuffled) - 2, round(len(shuffled) * 0.2)))
    return shuffled[validation_count:], shuffled[:validation_count]


def collate_batch(batch: list[tuple[torch.Tensor, str]]) -> tuple[torch.Tensor, list[str]]:
    images, texts = zip(*batch)
    return torch.stack(images), list(texts)


def encode_batch(
    backbone: nn.Module,
    image_projector: ProjectionHead,
    text_projector: ProjectionHead,
    images: torch.Tensor,
    texts: list[str],
    tokenizer: Any,
    device: torch.device,
) -> tuple[torch.Tensor, torch.Tensor]:
    images = images.to(device, non_blocking=True)
    tokens = tokenizer(texts).to(device, non_blocking=True)
    with torch.no_grad():
        image_features = backbone.encode_image(images).float()
        text_features = backbone.encode_text(tokens).float()
    return image_projector(image_features), text_projector(text_features)


def contrastive_loss(image_vectors: torch.Tensor, text_vectors: torch.Tensor, temperature: float) -> torch.Tensor:
    logits = (image_vectors @ text_vectors.T) / temperature
    labels = torch.arange(logits.shape[0], device=logits.device)
    return (F.cross_entropy(logits, labels) + F.cross_entropy(logits.T, labels)) * 0.5


def evaluate(
    backbone: nn.Module,
    image_projector: ProjectionHead,
    text_projector: ProjectionHead,
    loader: DataLoader,
    tokenizer: Any,
    device: torch.device,
    temperature: float,
) -> float:
    image_projector.eval()
    text_projector.eval()
    values: list[float] = []
    with torch.no_grad():
        for images, texts in loader:
            image_vectors, text_vectors = encode_batch(backbone, image_projector, text_projector, images, texts, tokenizer, device)
            values.append(float(contrastive_loss(image_vectors, text_vectors, temperature).item()))
    return sum(values) / max(1, len(values))


def save_checkpoint(
    output: Path,
    backbone_name: str,
    pretrained: str,
    image_projector: ProjectionHead,
    text_projector: ProjectionHead,
    optimizer: torch.optim.Optimizer,
    epoch: int,
    step: int,
    best_validation_loss: float,
    metrics: dict[str, Any],
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    bundle = {
        "format_version": 1,
        "backbone": backbone_name,
        "pretrained": pretrained,
        "image_projector": image_projector.state_dict(),
        "text_projector": text_projector.state_dict(),
        "optimizer": optimizer.state_dict(),
        "epoch": epoch,
        "step": step,
        "best_validation_loss": best_validation_loss,
        "metrics": metrics,
    }
    temporary = output.with_suffix(output.suffix + ".tmp")
    torch.save(bundle, temporary)
    temporary.replace(output)
    metrics_path = output.with_suffix(".metrics.json")
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def train(args: argparse.Namespace) -> dict[str, Any]:
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    torch.set_num_threads(max(1, min(8, torch.get_num_threads())))

    rows, license_counts = load_rows(args.pairs)
    train_rows, validation_rows = split_by_asset(rows, args.seed)
    try:
        import open_clip
    except ImportError as exc:
        raise SystemExit("Install multimodal dependencies: python -m pip install -r multimodal/requirements.txt") from exc

    print("Loading frozen visual encoder: " + args.model + " / " + args.pretrained, flush=True)
    backbone, train_transform, validation_transform = open_clip.create_model_and_transforms(
        args.model, pretrained=args.pretrained
    )
    tokenizer = open_clip.get_tokenizer(args.model)
    backbone.to(device).eval()
    for parameter in backbone.parameters():
        parameter.requires_grad_(False)
    image_dim = int(backbone.visual.output_dim)
    text_dim = int(backbone.text_projection.shape[-1])
    image_projector = ProjectionHead(image_dim).to(device)
    text_projector = ProjectionHead(text_dim).to(device)
    optimizer = torch.optim.AdamW(
        list(image_projector.parameters()) + list(text_projector.parameters()),
        lr=args.learning_rate,
        weight_decay=0.01,
    )

    start_epoch = 0
    total_steps = 0
    best_validation_loss = float("inf")
    if args.resume and args.output.exists():
        saved = torch.load(args.output, map_location="cpu", weights_only=False)
        if saved.get("backbone") != args.model or saved.get("pretrained") != args.pretrained:
            raise ValueError("Checkpoint backbone differs from requested model; use the matching model or a new output path.")
        image_projector.load_state_dict(saved["image_projector"])
        text_projector.load_state_dict(saved["text_projector"])
        if "optimizer" in saved:
            optimizer.load_state_dict(saved["optimizer"])
        start_epoch = int(saved.get("epoch", 0))
        total_steps = int(saved.get("step", 0))
        best_validation_loss = float(saved.get("best_validation_loss", float("inf")))
        print("Resuming after epoch " + str(start_epoch) + ", step " + str(total_steps), flush=True)

    train_loader = DataLoader(
        PairDataset(train_rows, train_transform),
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.workers,
        pin_memory=device.type == "cuda",
        collate_fn=collate_batch,
        drop_last=False,
    )
    validation_loader = DataLoader(
        PairDataset(validation_rows, validation_transform),
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.workers,
        pin_memory=device.type == "cuda",
        collate_fn=collate_batch,
        drop_last=False,
    )

    started = time.time()
    deadline = started + args.max_minutes * 60 if args.max_minutes > 0 else None
    trainable_parameters = sum(parameter.numel() for parameter in image_projector.parameters()) + sum(
        parameter.numel() for parameter in text_projector.parameters()
    )
    latest_train_loss = float("nan")
    completed_epochs = start_epoch
    stopped_for_time = False
    optimizer.zero_grad(set_to_none=True)
    try:
        for epoch_index in range(start_epoch, args.epochs):
            image_projector.train()
            text_projector.train()
            losses: list[float] = []
            for batch_index, (images, texts) in enumerate(train_loader, 1):
                image_vectors, text_vectors = encode_batch(
                    backbone, image_projector, text_projector, images, texts, tokenizer, device
                )
                loss = contrastive_loss(image_vectors, text_vectors, args.temperature)
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(
                    list(image_projector.parameters()) + list(text_projector.parameters()), 1.0
                )
                optimizer.step()
                total_steps += 1
                latest_train_loss = float(loss.item())
                losses.append(latest_train_loss)
                if total_steps == 1 or total_steps % args.log_every == 0:
                    print(
                        "epoch=" + str(epoch_index + 1) + "/" + str(args.epochs)
                        + " step=" + str(total_steps)
                        + " batch_loss=" + format(latest_train_loss, ".5f"),
                        flush=True,
                    )
                if args.max_steps > 0 and total_steps >= args.max_steps:
                    break
                if deadline is not None and time.time() >= deadline:
                    stopped_for_time = True
                    break
            completed_epochs = epoch_index + 1
            validation_loss = evaluate(
                backbone, image_projector, text_projector, validation_loader, tokenizer, device, args.temperature
            )
            if validation_loss < best_validation_loss:
                best_validation_loss = validation_loss
            metrics = {
                "status": "running",
                "device": str(device),
                "backbone": args.model,
                "pretrained": args.pretrained,
                "backbone_frozen": True,
                "trainable_parameters": trainable_parameters,
                "pairs_accepted": len(rows),
                "train_pairs": len(train_rows),
                "validation_pairs": len(validation_rows),
                "license_counts": dict(license_counts),
                "epoch": completed_epochs,
                "epochs_requested": args.epochs,
                "steps": total_steps,
                "mean_train_loss_last_epoch": round(sum(losses) / max(1, len(losses)), 6),
                "latest_batch_loss": round(latest_train_loss, 6),
                "validation_loss": round(validation_loss, 6),
                "best_validation_loss": round(best_validation_loss, 6),
                "elapsed_seconds": round(time.time() - started, 2),
                "stopped_for_time_limit": stopped_for_time,
                "checkpoint": str(args.output),
                "note": "This is a contrastive retrieval adapter, not a pixel/video/3D generator.",
            }
            save_checkpoint(
                args.output, args.model, args.pretrained, image_projector, text_projector,
                optimizer, completed_epochs, total_steps, best_validation_loss, metrics
            )
            print(json.dumps(metrics, ensure_ascii=False), flush=True)
            if args.max_steps > 0 and total_steps >= args.max_steps:
                break
            if stopped_for_time:
                break
    except KeyboardInterrupt:
        metrics = {
            "status": "interrupted_checkpoint_saved",
            "backbone": args.model,
            "pretrained": args.pretrained,
            "epoch": completed_epochs,
            "steps": total_steps,
            "pairs_accepted": len(rows),
            "elapsed_seconds": round(time.time() - started, 2),
            "checkpoint": str(args.output),
        }
        save_checkpoint(
            args.output, args.model, args.pretrained, image_projector, text_projector,
            optimizer, completed_epochs, total_steps, best_validation_loss, metrics
        )
        print(json.dumps(metrics, ensure_ascii=False), flush=True)
        return metrics

    final_metrics = {
        "status": "trained",
        "device": str(device),
        "backbone": args.model,
        "pretrained": args.pretrained,
        "backbone_frozen": True,
        "trainable_parameters": trainable_parameters,
        "pairs_accepted": len(rows),
        "train_pairs": len(train_rows),
        "validation_pairs": len(validation_rows),
        "license_counts": dict(license_counts),
        "epochs_completed": completed_epochs,
        "epochs_requested": args.epochs,
        "steps": total_steps,
        "latest_batch_loss": round(latest_train_loss, 6),
        "best_validation_loss": round(best_validation_loss, 6),
        "elapsed_seconds": round(time.time() - started, 2),
        "stopped_for_time_limit": stopped_for_time,
        "checkpoint": str(args.output),
        "note": "This is a contrastive retrieval adapter, not a pixel/video/3D generator.",
    }
    save_checkpoint(
        args.output, args.model, args.pretrained, image_projector, text_projector,
        optimizer, completed_epochs, total_steps, best_validation_loss, final_metrics
    )
    print(json.dumps(final_metrics, ensure_ascii=False), flush=True)
    return final_metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a resumable MotionForge visual retrieval adapter.")
    parser.add_argument("--pairs", type=Path, default=Path("datasets/pairs.jsonl"))
    parser.add_argument("--model", default="ViT-B-32")
    parser.add_argument("--pretrained", default="laion2b_s34b_b79k")
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--max-steps", type=int, default=0)
    parser.add_argument("--max-minutes", type=float, default=0)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--learning-rate", type=float, default=0.0001)
    parser.add_argument("--temperature", type=float, default=0.07)
    parser.add_argument("--log-every", type=int, default=25)
    parser.add_argument("--seed", type=int, default=20261113)
    parser.add_argument("--output", type=Path, default=Path("artifacts/multimodal/visual_adapter.pt"))
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.epochs < 1 or args.epochs > 100:
        raise ValueError("epochs must be between 1 and 100.")
    if args.max_steps < 0 or args.max_minutes < 0:
        raise ValueError("max-steps and max-minutes must be >= 0.")
    if args.batch_size < 2 or args.batch_size > 128 or args.workers < 0 or args.workers > 8:
        raise ValueError("batch-size must be 2-128 and workers 0-8.")
    if args.learning_rate <= 0 or args.temperature <= 0 or args.log_every < 1:
        raise ValueError("learning-rate, temperature and log-every must be positive.")
    train(args)


if __name__ == "__main__":
    main()
