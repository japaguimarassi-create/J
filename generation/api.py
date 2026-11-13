from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import secrets
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"
UPLOADS = OUTPUTS / "uploads"
WORKFLOWS = ROOT / "generation" / "workflows"
OUTPUTS.mkdir(parents=True, exist_ok=True)
UPLOADS.mkdir(parents=True, exist_ok=True)
WORKFLOWS.mkdir(parents=True, exist_ok=True)

HOST = os.environ.get("MOTIONFORGE_GENERATION_HOST", "127.0.0.1").strip()
API_KEY = os.environ.get("MOTIONFORGE_GENERATION_KEY", "").strip()
if HOST.lower() not in {"127.0.0.1", "localhost", "::1"} and not API_KEY:
    raise RuntimeError("MOTIONFORGE_GENERATION_KEY is required when binding outside loopback.")

app = FastAPI(title="MotionForge Generation API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)
app.mount("/outputs", StaticFiles(directory=str(OUTPUTS)), name="outputs")


@app.middleware("http")
async def local_api_guard(request: Any, call_next: Any) -> Any:
    if request.url.path.startswith("/api/") and API_KEY:
        supplied = request.headers.get("Authorization", "")
        if not supplied.startswith("Bearer ") or not secrets.compare_digest(supplied[7:], API_KEY):
            return JSONResponse(status_code=401, content={"error": "Missing or invalid MotionForge generation key."})
    return await call_next(request)


def safe_filename(value: str, default: str = "upload") -> str:
    name = Path(value.replace("\\", "/")).name
    name = re.sub(r"[^a-zA-Z0-9._-]+", "-", name).strip("-.")
    return name[:100] or default


def run_command(command: list[str], timeout: int) -> dict[str, Any]:
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=504, detail="Generation timed out. The GPU job may still require manual cleanup.") from exc
    output = (result.stdout or "")[-12000:]
    error = (result.stderr or "")[-12000:]
    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail={"error": "Generation process failed.", "exit_code": result.returncode, "stdout": output, "stderr": error},
        )
    parsed: dict[str, Any] = {"stdout": output}
    decoder = json.JSONDecoder()
    for position in range(len(output) - 1, -1, -1):
        if output[position] != "{":
            continue
        try:
            candidate, _ = decoder.raw_decode(output[position:])
            if isinstance(candidate, dict):
                parsed = candidate
                break
        except json.JSONDecodeError:
            continue
    parsed["process_exit_code"] = result.returncode
    return parsed


def save_upload(upload: UploadFile, allowed_extensions: set[str], limit_mb: int = 20) -> Path:
    filename = safe_filename(upload.filename or "")
    extension = Path(filename).suffix.lower()
    if extension not in allowed_extensions:
        raise HTTPException(status_code=415, detail="Unsupported input file type.")
    target = UPLOADS / (secrets.token_hex(8) + extension)
    total = 0
    limit = limit_mb * 1024 * 1024
    try:
        with target.open("wb") as output:
            while True:
                chunk = upload.file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > limit:
                    raise HTTPException(status_code=413, detail="Upload exceeds the " + str(limit_mb) + " MB limit.")
                output.write(chunk)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    if total == 0:
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Empty upload.")
    return target


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "service": "MotionForge Generation API",
        "host": HOST,
        "image": "SDXL Diffusers",
        "video": "ComfyUI workflow API",
        "model3d": "Hunyuan3D-2.1",
        "outputs": "/outputs/",
    }


@app.post("/api/image")
def generate_image(
    prompt: str = Form(...),
    negative_prompt: str = Form(""),
    width: int = Form(1024),
    height: int = Form(1024),
    steps: int = Form(30),
    guidance: float = Form(7.0),
    seed: int = Form(20261113),
    lora_path: str = Form(""),
    init_image: UploadFile | None = File(None),
) -> dict[str, Any]:
    if not prompt.strip() or len(prompt) > 4000 or len(negative_prompt) > 4000:
        raise HTTPException(status_code=400, detail="Prompt must contain 1-4000 characters.")
    if width not in {512, 768, 1024, 1280, 1536} or height not in {512, 768, 1024, 1280, 1536}:
        raise HTTPException(status_code=400, detail="Unsupported image dimensions.")
    if steps < 1 or steps > 100 or guidance < 0 or guidance > 20:
        raise HTTPException(status_code=400, detail="Invalid steps or guidance.")
    command = [
        sys.executable, "-m", "generation.image",
        "--prompt", prompt,
        "--negative-prompt", negative_prompt,
        "--width", str(width),
        "--height", str(height),
        "--steps", str(steps),
        "--guidance", str(guidance),
        "--seed", str(seed),
        "--output", str(OUTPUTS / ("image-" + secrets.token_hex(6) + ".png")),
        "--low-vram",
    ]
    if lora_path.strip():
        candidate = Path(lora_path).resolve()
        lora_root = (ROOT / "artifacts" / "generation").resolve()
        if lora_root not in candidate.parents or not candidate.exists():
            raise HTTPException(status_code=400, detail="LoRA must be selected from artifacts/generation.")
        command.extend(["--lora", str(candidate)])
    if init_image is not None:
        image_path = save_upload(init_image, {".png", ".jpg", ".jpeg", ".webp"})
        command.extend(["--init-image", str(image_path)])
    result = run_command(command, timeout=3600)
    result["url"] = "/outputs/" + Path(str(result.get("output", ""))).name
    return result


@app.post("/api/video")
def generate_video(
    prompt: str = Form(...),
    workflow_name: str = Form(...),
    comfy_url: str = Form("http://127.0.0.1:8188"),
    prompt_node: str = Form(""),
    prompt_input: str = Form("text"),
    image_node: str = Form(""),
    image_input: str = Form("image"),
    init_image: UploadFile | None = File(None),
) -> dict[str, Any]:
    if not prompt.strip() or len(prompt) > 4000:
        raise HTTPException(status_code=400, detail="Prompt must contain 1-4000 characters.")
    workflow_file = safe_filename(workflow_name)
    if not workflow_file.endswith(".json"):
        raise HTTPException(status_code=400, detail="Workflow file must end in .json.")
    workflow_path = (WORKFLOWS / workflow_file).resolve()
    if WORKFLOWS.resolve() not in workflow_path.parents or not workflow_path.is_file():
        raise HTTPException(status_code=404, detail="Workflow not found in generation/workflows.")
    if not comfy_url.startswith(("http://127.0.0.1", "http://localhost", "http://[::1]", "https://")):
        raise HTTPException(status_code=400, detail="Use HTTPS or a loopback ComfyUI URL.")
    command = [
        sys.executable, "-m", "generation.video_comfy",
        "--comfy-url", comfy_url,
        "--workflow", str(workflow_path),
        "--prompt-text", prompt,
        "--output-dir", str(OUTPUTS / "video"),
    ]
    if prompt_node.strip():
        command.extend(["--prompt-node", prompt_node, "--prompt-input", prompt_input])
    if init_image is not None:
        if not image_node.strip():
            raise HTTPException(status_code=400, detail="image_node is required when an initial image is uploaded.")
        image_path = save_upload(init_image, {".png", ".jpg", ".jpeg", ".webp"})
        command.extend(["--image", str(image_path), "--image-node", image_node, "--image-input", image_input])
    result = run_command(command, timeout=86400)
    result["urls"] = ["/outputs/video/" + Path(path).name for path in result.get("outputs", [])]
    return result


@app.post("/api/model3d")
def generate_3d(
    texture: bool = Form(False),
    image: UploadFile = File(...),
) -> dict[str, Any]:
    image_path = save_upload(image, {".png", ".jpg", ".jpeg", ".webp"})
    output_path = OUTPUTS / "3d" / ("asset-" + secrets.token_hex(6) + ".glb")
    command = [
        sys.executable, "-m", "generation.model3d",
        "--image", str(image_path),
        "--output", str(output_path),
    ]
    if texture:
        command.append("--texture")
    result = run_command(command, timeout=86400)
    result["url"] = "/outputs/3d/" + output_path.name
    return result


def main() -> None:
    import uvicorn
    uvicorn.run(app, host=HOST, port=int(os.environ.get("MOTIONFORGE_GENERATION_PORT", "8189")))


if __name__ == "__main__":
    main()
