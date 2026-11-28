import argparse
import json
import re
from collections import OrderedDict
from pathlib import Path

import torch

from .runtime import KlodRuntime


class ShardedKlodRuntime:
    def __init__(
        self,
        manifest: str | Path,
        checkpoint_dir: str | Path,
        device: str | None = None,
        max_loaded_models: int = 2,
    ):
        self.manifest_path = Path(manifest).resolve()
        self.manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        self.checkpoint_dir = Path(checkpoint_dir).resolve()
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.max_loaded_models = max(1, int(max_loaded_models))
        self.cache = OrderedDict()
        self.shards = self.manifest.get("shards", [])
        self.base_dir = self.manifest_path.parent.parent

    def list_shards(self) -> list[dict]:
        result = []
        for shard in self.shards:
            checkpoint = self.checkpoint_dir / f"{shard['id']}.pt"
            result.append({
                "id": shard["id"],
                "domain": shard.get("domain", shard["id"]),
                "trained": checkpoint.is_file(),
                "checkpoint": str(checkpoint) if checkpoint.is_file() else None,
            })
        return result

    @property
    def available(self) -> bool:
        return any(item["trained"] for item in self.list_shards())

    def route(self, message: str) -> str:
        normalized = message.casefold()
        scored = []
        for index, shard in enumerate(self.shards):
            score = 0
            for keyword in shard.get("keywords", []):
                term = str(keyword).casefold().strip()
                if term and term in normalized:
                    score += max(1, len(term.split()))
            scored.append((score, -index, shard["id"]))
        if not scored:
            raise RuntimeError("No specialist shards are configured")
        winner = max(scored)
        if winner[0] == 0:
            default_id = self.manifest.get("default_shard", "conversation")
            return default_id if any(s["id"] == default_id for s in self.shards) else self.shards[0]["id"]
        return winner[2]

    def _load(self, shard_id: str) -> KlodRuntime:
        if shard_id in self.cache:
            self.cache.move_to_end(shard_id)
            return self.cache[shard_id]
        checkpoint = self.checkpoint_dir / f"{shard_id}.pt"
        if not checkpoint.is_file():
            raise FileNotFoundError(f"Specialist checkpoint not found: {checkpoint}")
        runtime = KlodRuntime(str(checkpoint), device=self.device)
        self.cache[shard_id] = runtime
        while len(self.cache) > self.max_loaded_models:
            self.cache.popitem(last=False)
        return runtime

    def chat_with_metadata(
        self,
        message: str,
        max_new_tokens: int = 180,
        force_shard: str | None = None,
    ) -> dict:
        requested = force_shard or self.route(message)
        available_ids = {
            item["id"] for item in self.list_shards() if item["trained"]
        }
        selected = requested
        if selected not in available_ids:
            default_id = self.manifest.get("default_shard", "conversation")
            if default_id in available_ids:
                selected = default_id
            elif available_ids:
                selected = sorted(available_ids)[0]
            else:
                raise RuntimeError("No trained specialist checkpoint is available")
        runtime = self._load(selected)
        response = runtime.chat(message, max_new_tokens=max_new_tokens)
        metadata = next(shard for shard in self.shards if shard["id"] == selected)
        return {
            "response": response,
            "shard_id": selected,
            "domain": metadata.get("domain", selected),
            "requested_shard": requested,
            "loaded_models": list(self.cache.keys()),
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke-test independently trained KLOD specialist shards")
    parser.add_argument("--manifest", type=Path, default=Path("config/shards.json"))
    parser.add_argument("--checkpoint-dir", type=Path, default=Path("runs/shards"))
    parser.add_argument("--device", default=None)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    runtime = ShardedKlodRuntime(args.manifest, args.checkpoint_dir, device=args.device)
    status = runtime.list_shards()
    print(json.dumps(status, indent=2, ensure_ascii=False))
    if args.smoke:
        for shard in status:
            if not shard["trained"]:
                continue
            result = runtime.chat_with_metadata(
                "Olá. Escreva uma resposta curta.",
                max_new_tokens=4,
                force_shard=shard["id"],
            )
            print(json.dumps({
                "shard_id": result["shard_id"],
                "domain": result["domain"],
                "response": result["response"],
            }, ensure_ascii=False))
        if not runtime.available:
            raise SystemExit("No trained shards found")


if __name__ == "__main__":
    main()
