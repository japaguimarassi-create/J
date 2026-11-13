from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import torch
from PIL import Image

DEFAULT_MODEL = "stabilityai/stable-diffusion-xl-base-1.0"


def build_pipeline(model_id: str, device: str, low_vram: bool, init_image: bool) -> Any:
    try:
        from diffusers import AutoPipelineForImage2Image, AutoPipelineForText2Image
    except ImportError as exc:
        raise SystemExit("Install image dependencies: python -m pip install -r generation/requirements.txt") from exc
    dtype = torch.float16 if device == "cuda" else torch.float32
    pipeline_class = AutoPipelineForImage2Image if init_image else AutoPipelineForText2Image
    pipeline = pipeline_class.from_pretrained(
        model_id,
        torch_dtype=dtype,
        use_safetensors=True,
        variant="fp16" if device == "cuda" else None,
    )
    if low_vram and device == "cuda":
        pipeline.enable_model_cpu_offload()
    else:
        pipeline = pipeline.to(device)
    if hasattr(pipeline, "enable_vae_slicing"):
        pipeline.enable_vae_slicing()
    if hasattr(pipeline, "enable_vae_tiling"):
        pipeline.enable_vae_tiling()
    return pipeline


def validate_dimensions(width: int, height: int) -> None:
    if width < 512 or height < 512 or width > 1536 or height > 1536:
        raise ValueError("Width and height must be between 512 and 1536.")
    if width % 8 or height % 8:
        raise ValueError("Width and height must be divisible by 8.")


def generate(args: argparse.Namespace) -> dict[str, Any]:
    if not torch.cuda.is_available() and not args.allow_cpu:
        raise RuntimeError("SDXL requires a suitable accelerator for practical use. Use Colab GPU or pass --allow-cpu knowingly.")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda" and args.low_vram:
        torch.backends.cuda.matmul.allow_tf32 = True
    validate_dimensions(args.width, args.height)
    init_image = Image.open(args.init_image).convert("RGB") if args.init_image else None
    pipeline = build_pipeline(args.model, device, args.low_vram, bool(init_image))
    if args.lora:
        pipeline.load_lora_weights(args.lora, adapter_name="motionforge")
        if args.fuse_lora:
            pipeline.fuse_lora(adapter_names=["motionforge"])
    generator = torch.Generator(device=device).manual_seed(args.seed)
    options: dict[str, Any] = {
        "prompt": args.prompt,
        "negative_prompt": args.negative_prompt or None,
        "width": args.width,
        "height": args.height,
        "num_inference_steps": args.steps,
        "guidance_scale": args.guidance,
        "generator": generator,
    }
    if init_image is not None:
        init_image.thumbnail((args.width, args.height), Image.Resampling.LANCZOS)
        options["image"] = init_image
        options["strength"] = args.strength
    started = time.time()
    with torch.inference_mode():
        result = pipeline(**options)
    image = result.images[0]
    output = args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, format="PNG", optimize=True)
    metadata = {
        "task": "image-to-image" if init_image else "text-to-image",
        "model": args.model,
        "prompt": args.prompt,
        "negative_prompt": args.negative_prompt,
        "seed": args.seed,
        "width": args.width,
        "height": args.height,
        "steps": args.steps,
        "guidance": args.guidance,
        "device": device,
        "lora": args.lora,
        "elapsed_seconds": round(time.time() - started, 2),
        "output": str(output.resolve()),
        "license": "CreativeML Open RAIL++-M; review the model license and usage restrictions before deployment.",
    }
    output.with_suffix(".json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate or transform an image with SDXL.")
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--negative-prompt", default="")
    parser.add_argument("--init-image", type=Path)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--lora")
    parser.add_argument("--fuse-lora", action="store_true")
    parser.add_argument("--width", type=int, default=1024)
    parser.add_argument("--height", type=int, default=1024)
    parser.add_argument("--steps", type=int, default=30)
    parser.add_argument("--guidance", type=float, default=7.0)
    parser.add_argument("--strength", type=float, default=0.75)
    parser.add_argument("--seed", type=int, default=20261113)
    parser.add_argument("--low-vram", action="store_true")
    parser.add_argument("--allow-cpu", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("outputs/image.png"))
    args = parser.parse_args()
    if not args.prompt.strip() or args.steps < 1 or args.steps > 100:
        raise ValueError("Prompt is required and steps must be 1-100.")
    if args.guidance < 0 or args.guidance > 20 or not 0.05 <= args.strength <= 1:
        raise ValueError("guidance must be 0-20 and strength 0.05-1.")
    if args.init_image and not args.init_image.is_file():
        raise FileNotFoundError(args.init_image)
    if args.lora and not Path(args.lora).exists():
        raise FileNotFoundError("LoRA path not found: " + args.lora)
    print(json.dumps(generate(args), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
