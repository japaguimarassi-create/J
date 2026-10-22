import argparse
import hashlib
import json
from pathlib import Path

import torch


TENSOR_LAYOUT = (
    "hidden_scale",
    "hidden_bias",
    "embedding.weight",
    "recurrent.weight_ih_l0",
    "recurrent.weight_hh_l0",
    "recurrent.bias_ih_l0",
    "recurrent.bias_hh_l0",
    "output.weight",
    "output.bias",
)
GROUP_SHAPES = (
    (88,),
    (88,),
    (256, 64),
    (264, 64),
    (264, 88),
    (264,),
    (264,),
    (256, 88),
    (256,),
)
PARAMETERS_PER_GROUP = 80_000
GROUP_COUNT = 5


def export_checkpoint(checkpoint_path: Path, output_path: Path, metadata_path: Path) -> dict:
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    if not isinstance(checkpoint, dict):
        raise ValueError("Checkpoint root must be a dictionary.")
    if checkpoint.get("model_type") != "DetaFiveGroupModel":
        raise ValueError("The checkpoint is not the original DetaFiveGroupModel.")
    if int(checkpoint.get("groups_completed", 0)) != GROUP_COUNT:
        raise ValueError("All five original Deta groups must be present.")
    state = checkpoint.get("model_state_dict")
    if not isinstance(state, dict):
        raise ValueError("Checkpoint has no model weights.")

    payload = bytearray()
    parameter_count = 0
    for group_index in range(GROUP_COUNT):
        prefix = f"groups.{group_index}."
        group_count = 0
        for tensor_name, expected_shape in zip(TENSOR_LAYOUT, GROUP_SHAPES):
            key = prefix + tensor_name
            tensor = state.get(key)
            if tensor is None:
                raise ValueError(f"Missing model tensor: {key}")
            tensor = tensor.detach().to(device="cpu", dtype=torch.float32).contiguous()
            if tuple(tensor.shape) != expected_shape:
                raise ValueError(f"Invalid shape for {key}: {tuple(tensor.shape)}")
            values = tensor.numpy().astype("<f4", copy=False)
            encoded = values.tobytes(order="C")
            if len(encoded) != tensor.numel() * 4:
                raise ValueError(f"Invalid binary length for {key}")
            if not all(map(lambda value: value == value and abs(value) != float("inf"), values.reshape(-1))):
                raise ValueError(f"Non-finite model values found in {key}")
            payload.extend(encoded)
            group_count += tensor.numel()
        if group_count != PARAMETERS_PER_GROUP:
            raise ValueError(f"Group {group_index + 1} contains {group_count} parameters.")
        parameter_count += group_count

    if parameter_count != 400_000 or len(payload) != 1_600_000:
        raise ValueError(f"Invalid model export: {parameter_count} parameters, {len(payload)} bytes.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(payload)
    metadata = {
        "model_type": checkpoint["model_type"],
        "parameters": parameter_count,
        "groups": GROUP_COUNT,
        "parameters_per_group": PARAMETERS_PER_GROUP,
        "training_steps": int(checkpoint.get("training_steps", 0)),
        "cumulative_training_steps": int(checkpoint.get("cumulative_training_steps", checkpoint.get("training_steps", 0))),
        "dataset_sha256": checkpoint.get("dataset_sha256", ""),
        "checkpoint_sha256": hashlib.sha256(checkpoint_path.read_bytes()).hexdigest(),
        "weights_sha256": hashlib.sha256(payload).hexdigest(),
        "binary_format": "little-endian IEEE754 float32, fixed tensor layout v1",
    }
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    args = parser.parse_args()
    metadata = export_checkpoint(args.checkpoint, args.output, args.metadata)
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
