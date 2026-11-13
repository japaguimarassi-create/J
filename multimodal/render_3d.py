from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ALLOWED = {"CC0-1.0", "CC-BY-4.0"}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def safe_name(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-.")[:100] or "asset"


def render_asset(asset_path: Path, output_dir: Path, asset_id: str, views: int, resolution: int) -> int:
    try:
        import bpy
        from mathutils import Vector
    except ImportError as exc:
        raise SystemExit("This script must be launched by Blender: blender --background --python multimodal/render_3d.py -- ...") from exc

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    ext = asset_path.suffix.lower()
    if ext in {".glb", ".gltf"}:
        bpy.ops.import_scene.gltf(filepath=str(asset_path))
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=str(asset_path))
    elif ext == ".obj":
        if hasattr(bpy.ops.wm, "obj_import"):
            bpy.ops.wm.obj_import(filepath=str(asset_path))
        else:
            bpy.ops.import_scene.obj(filepath=str(asset_path))
    elif ext == ".stl":
        if hasattr(bpy.ops.wm, "stl_import"):
            bpy.ops.wm.stl_import(filepath=str(asset_path))
        else:
            bpy.ops.import_mesh.stl(filepath=str(asset_path))
    else:
        raise ValueError("Unsupported 3D extension: " + ext)

    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not meshes:
        raise RuntimeError("No mesh objects were imported.")
    corners = [obj.matrix_world @ Vector(corner) for obj in meshes for corner in obj.bound_box]
    minimum = Vector((min(p.x for p in corners), min(p.y for p in corners), min(p.z for p in corners)))
    maximum = Vector((max(p.x for p in corners), max(p.y for p in corners), max(p.z for p in corners)))
    center = (minimum + maximum) * 0.5
    largest = max(maximum.x - minimum.x, maximum.y - minimum.y, maximum.z - minimum.z)
    if largest <= 1e-8:
        raise RuntimeError("The imported object has an empty bounding box.")
    scale = 2.2 / largest
    for obj in meshes:
        obj.location -= center
        obj.scale = obj.scale * scale

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in {item.identifier for item in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items} else "BLENDER_EEVEE"
    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "Standard"
    scene.render.image_settings.color_mode = "RGBA"
    if scene.world is None:
        scene.world = bpy.data.worlds.new("MotionForgeWorld")
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    if background:
        background.inputs["Color"].default_value = (0.72, 0.75, 0.8, 1.0)
        background.inputs["Strength"].default_value = 0.8

    def add_area(name: str, location: tuple[float, float, float], energy: float, size: float) -> None:
        light_data = bpy.data.lights.new(name=name, type="AREA")
        light_data.energy = energy
        light_data.shape = "DISK"
        light_data.size = size
        light_obj = bpy.data.objects.new(name, light_data)
        scene.collection.objects.link(light_obj)
        light_obj.location = location
        light_obj.rotation_euler = (Vector((0, 0, 0)) - light_obj.location).to_track_quat("-Z", "Y").to_euler()

    add_area("MotionForgeKey", (4, -4, 5), 900, 5)
    add_area("MotionForgeFill", (-4, -1, 2), 500, 4)
    add_area("MotionForgeRim", (0, 4, 4), 1100, 3)
    camera_data = bpy.data.cameras.new("MotionForgeCamera")
    camera = bpy.data.objects.new("MotionForgeCamera", camera_data)
    scene.collection.objects.link(camera)
    camera_data.lens = 52
    scene.camera = camera

    output_dir.mkdir(parents=True, exist_ok=True)
    rendered = 0
    for index in range(views):
        angle = (2.0 * 3.141592653589793 * index) / views
        camera.location = (4.2 * __import__("math").cos(angle), 4.2 * __import__("math").sin(angle), 2.0)
        camera.rotation_euler = (Vector((0, 0, 0)) - camera.location).to_track_quat("-Z", "Y").to_euler()
        target = output_dir / (safe_name(asset_id) + "_v" + str(index).zfill(2) + ".png")
        scene.render.filepath = str(target)
        bpy.ops.render.render(write_still=True)
        rendered += 1
    return rendered


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description="Render approved 3D dataset objects into multiple visual views.")
    parser.add_argument("--manifest", type=Path, default=Path("datasets/assets.jsonl"))
    parser.add_argument("--preview-dir", type=Path, default=Path("datasets/previews"))
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--views", type=int, default=6)
    parser.add_argument("--resolution", type=int, default=512)
    args = parser.parse_args(argv)
    if args.limit < 1 or args.views < 1 or args.views > 12 or args.resolution < 128 or args.resolution > 1024:
        raise ValueError("Use limit >= 1, views 1-12 and resolution 128-1024.")
    rows = read_jsonl(args.manifest)
    attempted = 0
    succeeded = 0
    rendered_views = 0
    skipped = 0
    errors: list[dict[str, str]] = []
    for row in rows:
        if attempted >= args.limit:
            break
        if row.get("media_type") != "3d" or row.get("rights_verified") is not True or row.get("license") not in ALLOWED:
            skipped += 1
            continue
        asset_id = str(row.get("asset_id", ""))
        asset_path = Path(str(row.get("local_path", ""))).expanduser()
        if not asset_id or not asset_path.is_file():
            skipped += 1
            continue
        existing = list(args.preview_dir.glob(safe_name(asset_id) + "_v*.png"))
        if len(existing) >= args.views:
            succeeded += 1
            rendered_views += len(existing)
            continue
        attempted += 1
        try:
            count = render_asset(asset_path, args.preview_dir, asset_id, args.views, args.resolution)
            rendered_views += count
            succeeded += 1
            print("rendered " + asset_id + " views=" + str(count), flush=True)
        except Exception as exc:
            errors.append({"asset_id": asset_id, "error": str(exc)[:500]})
            print("failed " + asset_id + ": " + str(exc), flush=True)
    print(json.dumps({
        "attempted": attempted,
        "succeeded": succeeded,
        "rendered_views": rendered_views,
        "skipped": skipped,
        "errors": errors[:100],
        "preview_dir": str(args.preview_dir.resolve()),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
