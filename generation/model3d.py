from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from PIL import Image

MODEL_ID = "tencent/Hunyuan3D-2.1"


def export_mesh(mesh: Any, destination: Path) -> None:
    candidate = mesh[0] if isinstance(mesh, (list, tuple)) and mesh else mesh
    if hasattr(candidate, "export"):
        candidate.export(str(destination))
        return
    if isinstance(candidate, dict) and "vertices" in candidate and "faces" in candidate:
        import trimesh
        trimesh.Trimesh(
            vertices=candidate["vertices"],
            faces=candidate["faces"],
            process=False,
        ).export(str(destination))
        return
    raise TypeError("Unsupported Hunyuan mesh output type: " + type(candidate).__name__)


def load_hunyuan(root: Path, model_id: str) -> tuple[Any, Any, Any]:
    if not root.is_dir():
        raise FileNotFoundError(
            "Hunyuan3D source checkout not found. Clone https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1 "
            "into " + str(root)
        )
    shape_path = str(root / "hy3dshape")
    paint_path = str(root / "hy3dpaint")
    for item in (shape_path, paint_path):
        if item not in sys.path:
            sys.path.insert(0, item)
    try:
        from hy3dshape.pipelines import Hunyuan3DDiTFlowMatchingPipeline
    except ImportError as exc:
        raise RuntimeError("Hunyuan3D dependencies are incomplete. Follow the upstream CUDA 12.4 / PyTorch 2.5.1 install guide.") from exc
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError("Hunyuan3D-2.1 shape generation requires a CUDA GPU for practical use.")
    shape_pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(model_id)
    if hasattr(shape_pipeline, "to"):
        shape_pipeline = shape_pipeline.to("cuda")
    paint_pipeline = None
    paint_config = None
    return shape_pipeline, paint_pipeline, paint_config


def generate(args: argparse.Namespace) -> dict[str, Any]:
    input_image = args.image.resolve()
    if not input_image.is_file():
        raise FileNotFoundError(input_image)
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    started = time.time()
    shape_pipeline, _, _ = load_hunyuan(args.hunyuan_root.resolve(), args.model)
    mesh = shape_pipeline(image=str(input_image))[0]
    if args.texture:
        for item in (str(args.hunyuan_root / "hy3dpaint"),):
            if item not in sys.path:
                sys.path.insert(0, item)
        try:
            from textureGenPipeline import Hunyuan3DPaintConfig, Hunyuan3DPaintPipeline
        except ImportError as exc:
            raise RuntimeError("Hunyuan3D paint dependencies are incomplete. Follow the upstream mesh rasterizer and renderer installation steps.") from exc
        temporary_mesh = output.with_name(output.stem + "_shape.glb")
        export_mesh(mesh, temporary_mesh)
        paint_pipeline = Hunyuan3DPaintPipeline(
            Hunyuan3DPaintConfig(max_num_view=args.paint_views, resolution=args.paint_resolution)
        )
        painted_mesh = paint_pipeline(str(temporary_mesh), image_path=str(input_image))
        export_mesh(painted_mesh, output)
        temporary_mesh.unlink(missing_ok=True)
    else:
        export_mesh(mesh, output)
    report = {
        "task": "image-to-3d",
        "model": args.model,
        "input_image": str(input_image),
        "output": str(output),
        "textured": bool(args.texture),
        "device": "cuda",
        "elapsed_seconds": round(time.time() - started, 2),
        "license": "Tencent Hunyuan 3D 2.1 Community License; read the complete license and check Territory and acceptable-use restrictions.",
        "training_policy": "Do not use this model's output or results to improve any other AI model.",
        "model_notice": "Tencent Hunyuan 3D 2.1 is not affiliated with or endorsed by MotionForge.",
    }
    output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a 3D mesh from an image using the official Hunyuan3D-2.1 pipeline.")
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("outputs/3d/asset.glb"))
    parser.add_argument("--hunyuan-root", type=Path, default=Path("third_party/Hunyuan3D-2.1"))
    parser.add_argument("--model", default=MODEL_ID)
    parser.add_argument("--texture", action="store_true")
    parser.add_argument("--paint-views", type=int, default=6)
    parser.add_argument("--paint-resolution", type=int, default=512)
    args = parser.parse_args()
    if args.texture and not 1 <= args.paint_views <= 12:
        raise ValueError("paint-views must be 1-12.")
    if args.texture and not 256 <= args.paint_resolution <= 1024:
        raise ValueError("paint-resolution must be 256-1024.")
    print(json.dumps(generate(args), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
