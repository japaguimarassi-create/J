import argparse
import hashlib
import json
import math
import os
import tempfile
import sys
from pathlib import Path

import torch


MAGIC = b"DTA400K1"
EXPECTED_PARAMETERS = 400_000
EXPECTED_GROUP_PARAMETERS = 80_000


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def export_checkpoint(checkpoint_path: str | Path, weights_path: str | Path, metadata_path: str | Path) -> dict:
    if sys.byteorder != "little":
        raise RuntimeError("The Android weights exporter requires a little-endian host.")
    source = Path(checkpoint_path)
    if not source.is_file() or source.stat().st_size == 0:
        raise FileNotFoundError(f"Checkpoint is missing or empty: {source}")

    checkpoint = torch.load(source, map_location="cpu", weights_only=True)
    if not isinstance(checkpoint, dict) or checkpoint.get("model_type") != "DetaFiveGroupModel":
        raise ValueError("Expected a DetaFiveGroupModel checkpoint.")
    if int(checkpoint.get("groups_completed", -1)) != 5:
        raise ValueError("The Android export requires all five trained groups.")
    config = checkpoint.get("config")
    state = checkpoint.get("model_state_dict")
    if not isinstance(config, dict) or not isinstance(state, dict):
        raise ValueError("Checkpoint does not include configuration and model weights.")
    if (config.get("vocab_size"), config.get("embedding_dim"), config.get("hidden_dim"), config.get("groups")) != (256, 64, 88, 5):
        raise ValueError("Checkpoint architecture does not match the Android inference engine.")
    if int(checkpoint.get("model_parameters", -1)) != EXPECTED_PARAMETERS:
        raise ValueError("Checkpoint parameter count is not 400,000.")

    weights_path = Path(weights_path)
    metadata_path = Path(metadata_path)
    weights_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)

    expected_shapes = [
        ("embedding.weight", (256, 64)),
        ("recurrent.weight_ih_l0", (264, 64)),
        ("recurrent.weight_hh_l0", (264, 88)),
        ("recurrent.bias_ih_l0", (264,)),
        ("recurrent.bias_hh_l0", (264,)),
        ("hidden_scale", (88,)),
        ("hidden_bias", (88,)),
        ("output.weight", (256, 88)),
        ("output.bias", (256,)),
    ]
    tensor_parameters = 0
    tensors = []
    group_counts = []
    for group_index in range(5):
        group_count = 0
        prefix = f"groups.{group_index}."
        for suffix, expected_shape in expected_shapes:
            key = prefix + suffix
            tensor = state.get(key)
            if not isinstance(tensor, torch.Tensor):
                raise ValueError(f"Missing model tensor: {key}")
            if tuple(tensor.shape) != expected_shape:
                raise ValueError(f"Unexpected shape for {key}: {tuple(tensor.shape)}")
            if not torch.is_floating_point(tensor):
                raise ValueError(f"Model tensor {key} must contain floating-point values.")
            detached = tensor.detach().cpu().to(dtype=torch.float32).contiguous()
            if not bool(torch.isfinite(detached).all()):
                raise ValueError(f"Model tensor {key} contains NaN or infinity.")
            tensors.append((key, detached))
            count = detached.numel()
            tensor_parameters += count
            group_count += count
        group_counts.append(group_count)

    if tensor_parameters != EXPECTED_PARAMETERS:
        raise ValueError(f"Export found {tensor_parameters} parameters instead of 400,000.")
    if group_counts != [EXPECTED_GROUP_PARAMETERS] * 5:
        raise ValueError(f"Unexpected per-group counts: {group_counts}")
    if len(state) != len(tensors):
        raise ValueError("Checkpoint has unexpected tensors; refusing a partial or ambiguous export.")

    weights_fd, weights_temp_name = tempfile.mkstemp(prefix=weights_path.name + ".", dir=weights_path.parent)
    metadata_fd, metadata_temp_name = tempfile.mkstemp(prefix=metadata_path.name + ".", dir=metadata_path.parent)
    try:
        with os.fdopen(weights_fd, "wb") as output:
            output.write(MAGIC)
            for _, tensor in tensors:
                output.write(bytes(tensor.view(-1).view(torch.uint8).tolist()))
            output.flush()
            os.fsync(output.fileno())
        expected_size = len(MAGIC) + EXPECTED_PARAMETERS * 4
        if Path(weights_temp_name).stat().st_size != expected_size:
            raise RuntimeError("Exported weight file has an unexpected byte length.")
        os.replace(weights_temp_name, weights_path)

        per_group_metrics = checkpoint.get("metrics_by_group", {})
        validation_losses = {}
        if isinstance(per_group_metrics, dict):
            for key, metrics in per_group_metrics.items():
                if isinstance(metrics, dict) and math.isfinite(float(metrics.get("validation_loss", float("nan")))):
                    validation_losses[str(key)] = float(metrics["validation_loss"])
        metadata = {
            "format": "DTA400K1",
            "architecture": "DetaFiveGroupModel",
            "parameter_count": tensor_parameters,
            "group_count": 5,
            "parameters_per_group": group_counts,
            "groups_completed": int(checkpoint["groups_completed"]),
            "training_steps_this_run": int(checkpoint.get("training_steps", 0)),
            "cumulative_training_steps": int(checkpoint.get("cumulative_training_steps", checkpoint.get("training_steps", 0))),
            "dataset_sha256": str(checkpoint.get("dataset_sha256", "")),
            "parent_checkpoint_sha256": str(checkpoint.get("training_lineage", {}).get("parent_checkpoint_sha256", "")),
            "validation_losses": validation_losses,
            "weights_file": weights_path.name,
            "weights_sha256": sha256_file(weights_path),
            "checkpoint_sha256": sha256_file(source),
            "runtime": "Pure Java GRU inference on Android; no external AI API",
        }
        with os.fdopen(metadata_fd, "w", encoding="utf-8") as output:
            json.dump(metadata, output, ensure_ascii=False, indent=2, sort_keys=True)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(metadata_temp_name, metadata_path)
    finally:
        for temporary in (weights_temp_name, metadata_temp_name):
            if os.path.exists(temporary):
                os.unlink(temporary)

    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(description="Export the trained Deta 400k model for pure-Java Android inference.")
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--weights-out", required=True)
    parser.add_argument("--metadata-out", required=True)
    args = parser.parse_args()
    result = export_checkpoint(args.checkpoint, args.weights_out, args.metadata_out)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
