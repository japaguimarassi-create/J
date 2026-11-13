from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import torch

DEFAULT_MODEL = "stabilityai/stable-diffusion-xl-base-1.0"


def train(args: argparse.Namespace) -> dict[str, Any]:
    if not torch.cuda.is_available():
        raise RuntimeError("SDXL LoRA training requires CUDA. Use a Colab GPU or another supported GPU host.")
    total_vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
    if total_vram < args.minimum_vram_gb:
        raise RuntimeError(
            "Detected " + format(total_vram, ".1f") + " GB VRAM; configured minimum is "
            + str(args.minimum_vram_gb) + " GB. Reduce memory settings or use a larger GPU."
        )
    diffusers_root = args.diffusers_root.resolve()
    script = diffusers_root / "examples" / "text_to_image" / "train_text_to_image_lora_sdxl.py"
    if not script.is_file():
        raise FileNotFoundError(
            "Diffusers training example not found: " + str(script)
            + ". Clone https://github.com/huggingface/diffusers into third_party/diffusers."
        )
    metadata = args.dataset_dir / "metadata.jsonl"
    if not metadata.is_file():
        raise FileNotFoundError("Prepared dataset metadata not found: " + str(metadata))
    with metadata.open("r", encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle if line.strip()]
    if len(rows) < 10:
        raise ValueError("Dataset has fewer than 10 captioned examples.")
    licenses = {str(row.get("license", "")) for row in rows}
    if not licenses.issubset({"CC0-1.0", "CC-BY-4.0"}):
        raise ValueError("Dataset contains a license outside the default allowlist: " + ", ".join(sorted(licenses)))
    missing = [
        str(row.get("file_name", ""))
        for row in rows
        if not (args.dataset_dir / str(row.get("file_name", ""))).is_file()
    ]
    if missing:
        raise FileNotFoundError("Dataset files missing, examples: " + ", ".join(missing[:5]))

    command = [
        sys.executable, "-m", "accelerate.commands.launch",
        "--num_processes", "1",
        str(script),
        "--pretrained_model_name_or_path", args.model,
        "--train_data_dir", str(args.dataset_dir.resolve()),
        "--image_column", "image",
        "--caption_column", "text",
        "--resolution", str(args.resolution),
        "--center_crop",
        "--train_batch_size", str(args.batch_size),
        "--gradient_accumulation_steps", str(args.gradient_accumulation),
        "--gradient_checkpointing",
        "--rank", str(args.rank),
        "--learning_rate", str(args.learning_rate),
        "--lr_scheduler", "constant",
        "--lr_warmup_steps", "0",
        "--max_train_steps", str(args.max_steps),
        "--checkpointing_steps", str(args.checkpoint_every),
        "--checkpoints_total_limit", "3",
        "--output_dir", str(args.output.resolve()),
        "--mixed_precision", args.mixed_precision,
        "--seed", str(args.seed),
        "--allow_tf32",
        "--report_to", "none",
    ]
    if args.use_8bit_adam:
        command.append("--use_8bit_adam")
    if args.resume:
        command.extend(["--resume_from_checkpoint", "latest"])
    if args.validation_prompt:
        command.extend(["--validation_prompt", args.validation_prompt, "--num_validation_images", "1"])
    args.output.mkdir(parents=True, exist_ok=True)
    report_path = args.output / "training_config.json"
    config = {
        "model": args.model,
        "dataset": str(args.dataset_dir.resolve()),
        "items": len(rows),
        "licenses": sorted(licenses),
        "gpu": torch.cuda.get_device_name(0),
        "vram_gb": round(total_vram, 2),
        "rank": args.rank,
        "max_steps": args.max_steps,
        "command": command,
        "model_license": "CreativeML Open RAIL++-M",
    }
    report_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Starting SDXL LoRA training on " + torch.cuda.get_device_name(0), flush=True)
    result = subprocess.run(command, cwd=diffusers_root, check=False)
    config["exit_code"] = result.returncode
    config["status"] = "completed" if result.returncode == 0 else "failed"
    report_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if result.returncode != 0:
        raise RuntimeError("Diffusers LoRA training failed with exit code " + str(result.returncode))
    config["lora_directory"] = str(args.output.resolve())
    return config


def main() -> None:
    parser = argparse.ArgumentParser(description="Train an SDXL LoRA on the approved MotionForge image dataset.")
    parser.add_argument("--dataset-dir", type=Path, default=Path("datasets/sdxl_lora"))
    parser.add_argument("--diffusers-root", type=Path, default=Path("third_party/diffusers"))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--output", type=Path, default=Path("artifacts/generation/sdxl-lora"))
    parser.add_argument("--steps", dest="max_steps", type=int, default=2000)
    parser.add_argument("--checkpoint-every", type=int, default=250)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation", type=int, default=4)
    parser.add_argument("--rank", type=int, default=16)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--resolution", type=int, default=1024)
    parser.add_argument("--mixed-precision", choices=["fp16", "bf16"], default="fp16")
    parser.add_argument("--minimum-vram-gb", type=float, default=12)
    parser.add_argument("--seed", type=int, default=20261113)
    parser.add_argument("--use-8bit-adam", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--validation-prompt", default="")
    args = parser.parse_args()
    if args.max_steps < 1 or args.max_steps > 100000 or args.checkpoint_every < 10:
        raise ValueError("steps must be 1-100000 and checkpoint-every at least 10.")
    if args.batch_size < 1 or args.batch_size > 8 or args.gradient_accumulation < 1 or args.gradient_accumulation > 64:
        raise ValueError("Invalid batch-size or gradient-accumulation.")
    if args.rank < 4 or args.rank > 128 or args.resolution not in {512, 768, 1024}:
        raise ValueError("rank must be 4-128 and resolution must be 512, 768 or 1024.")
    print(json.dumps(train(args), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
