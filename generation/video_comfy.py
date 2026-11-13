from __future__ import annotations

import argparse
import json
import mimetypes
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any


def request_json(base_url: str, route: str, payload: dict[str, Any] | None = None, timeout: int = 60) -> dict[str, Any]:
    url = base_url.rstrip("/") + route
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"} if data is not None else {},
        method="POST" if data is not None else "GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read(16_000_000).decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read(4000).decode("utf-8", errors="replace")
        raise RuntimeError("ComfyUI HTTP " + str(exc.code) + ": " + detail) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError("Could not reach ComfyUI at " + url + ": " + str(exc.reason)) from exc


def upload_image(base_url: str, path: Path, timeout: int = 120) -> dict[str, Any]:
    boundary = "----MotionForge" + uuid.uuid4().hex
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    content = path.read_bytes()
    body = (
        ("--" + boundary + "\r\n").encode()
        + ('Content-Disposition: form-data; name="image"; filename="' + path.name.replace('"', "") + '"\r\n').encode()
        + ("Content-Type: " + mime + "\r\n\r\n").encode()
        + content
        + ("\r\n--" + boundary + "\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n--" + boundary + "--\r\n").encode()
    )
    request = urllib.request.Request(
        base_url.rstrip("/") + "/upload/image",
        data=body,
        headers={"Content-Type": "multipart/form-data; boundary=" + boundary},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read(2_000_000).decode("utf-8"))
    except Exception as exc:
        raise RuntimeError("ComfyUI image upload failed: " + str(exc)) from exc
    if not result.get("name"):
        raise RuntimeError("ComfyUI did not return an uploaded image name.")
    return result


def set_node_input(workflow: dict[str, Any], node_id: str, input_name: str, value: Any) -> None:
    node = workflow.get(node_id)
    if not isinstance(node, dict):
        raise KeyError("Workflow node not found: " + node_id)
    inputs = node.get("inputs")
    if not isinstance(inputs, dict) or input_name not in inputs:
        raise KeyError("Input " + input_name + " not found in node " + node_id)
    inputs[input_name] = value


def parse_assignment(value: str) -> tuple[str, str, Any]:
    try:
        node_id, rest = value.split(".", 1)
        input_name, raw = rest.split("=", 1)
    except ValueError as exc:
        raise ValueError("--set must use NODE_ID.INPUT=JSON") from exc
    if not node_id or not input_name:
        raise ValueError("--set node id and input are required")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = raw
    return node_id, input_name, parsed


def find_output_files(history: dict[str, Any], selected_nodes: set[str]) -> list[dict[str, str]]:
    outputs = history.get("outputs") or {}
    result: list[dict[str, str]] = []
    for node_id, node_output in outputs.items():
        if selected_nodes and node_id not in selected_nodes:
            continue
        if not isinstance(node_output, dict):
            continue
        for key in ("videos", "gifs", "images"):
            for item in node_output.get(key, []) or []:
                if not isinstance(item, dict) or not item.get("filename"):
                    continue
                result.append({
                    "filename": str(item["filename"]),
                    "subfolder": str(item.get("subfolder", "")),
                    "type": str(item.get("type", "output")),
                    "media_key": key,
                    "node_id": str(node_id),
                })
    return result


def download_output(base_url: str, item: dict[str, str], output_dir: Path, timeout: int = 180) -> Path:
    query = urllib.parse.urlencode({
        "filename": item["filename"],
        "subfolder": item["subfolder"],
        "type": item["type"],
    })
    url = base_url.rstrip("/") + "/view?" + query
    request = urllib.request.Request(url)
    output_dir.mkdir(parents=True, exist_ok=True)
    name = Path(item["filename"]).name
    target = output_dir / name
    if not target.suffix:
        target = target.with_suffix(".mp4" if item["media_key"] == "videos" else ".gif")
    with urllib.request.urlopen(request, timeout=timeout) as response, target.open("wb") as handle:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
    if not target.is_file() or target.stat().st_size == 0:
        raise RuntimeError("ComfyUI returned an empty output: " + item["filename"])
    return target


def generate(args: argparse.Namespace) -> dict[str, Any]:
    workflow = json.loads(args.workflow.read_text(encoding="utf-8"))
    if not isinstance(workflow, dict) or not workflow:
        raise ValueError("Workflow must be a non-empty ComfyUI API-format JSON object.")
    prompt = workflow.get("prompt") if isinstance(workflow.get("prompt"), dict) else workflow
    if args.prompt_node:
        set_node_input(prompt, args.prompt_node, args.prompt_input, args.prompt_text)
    if args.negative_node:
        set_node_input(prompt, args.negative_node, args.negative_input, args.negative_text)
    if args.image:
        if not args.image.is_file():
            raise FileNotFoundError(args.image)
        uploaded = upload_image(args.comfy_url, args.image)
        if not args.image_node:
            raise ValueError("Use --image-node NODE_ID to connect the uploaded image to the workflow.")
        set_node_input(prompt, args.image_node, args.image_input, uploaded["name"])
    for assignment in args.set_value:
        node_id, input_name, value = parse_assignment(assignment)
        set_node_input(prompt, node_id, input_name, value)
    client_id = str(uuid.uuid4())
    queued = request_json(args.comfy_url, "/prompt", {
        "prompt": prompt,
        "client_id": client_id,
    }, timeout=60)
    prompt_id = queued.get("prompt_id")
    if not prompt_id:
        raise RuntimeError("ComfyUI did not accept the workflow: " + json.dumps(queued)[:4000])
    started = time.time()
    history: dict[str, Any] = {}
    while time.time() - started < args.timeout:
        response = request_json(args.comfy_url, "/history/" + urllib.parse.quote(str(prompt_id)), timeout=30)
        if prompt_id in response:
            history = response[prompt_id]
            status = history.get("status") or {}
            if status.get("completed") or history.get("outputs"):
                break
            if status.get("status_str") == "error":
                raise RuntimeError("ComfyUI workflow failed: " + json.dumps(status)[:4000])
        time.sleep(args.poll_seconds)
    else:
        raise TimeoutError("ComfyUI generation timed out after " + str(args.timeout) + " seconds. Prompt ID: " + str(prompt_id))
    output_files = find_output_files(history, set(args.output_node))
    if not output_files:
        raise RuntimeError("Workflow completed but no videos/images were found. Verify the SaveVideo/SaveAnimatedWEBP/SaveImage output node and --output-node.")
    saved = [str(download_output(args.comfy_url, item, args.output_dir)) for item in output_files]
    report = {
        "task": "image-to-video" if args.image else "text-to-video",
        "backend": args.comfy_url,
        "workflow": str(args.workflow),
        "prompt_id": prompt_id,
        "prompt": args.prompt_text,
        "outputs": saved,
        "elapsed_seconds": round(time.time() - started, 2),
        "note": "The selected ComfyUI workflow and loaded checkpoint determine quality, limits and model license.",
    }
    report_path = args.output_dir / ("video_" + str(prompt_id) + ".json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report["report"] = str(report_path.resolve())
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a ComfyUI API workflow for text-to-video or image-to-video.")
    parser.add_argument("--comfy-url", default="http://127.0.0.1:8188")
    parser.add_argument("--workflow", type=Path, required=True)
    parser.add_argument("--prompt-text", required=True)
    parser.add_argument("--prompt-node")
    parser.add_argument("--prompt-input", default="text")
    parser.add_argument("--negative-text", default="")
    parser.add_argument("--negative-node")
    parser.add_argument("--negative-input", default="text")
    parser.add_argument("--image", type=Path)
    parser.add_argument("--image-node")
    parser.add_argument("--image-input", default="image")
    parser.add_argument("--set", dest="set_value", action="append", default=[], help="Override workflow input: NODE_ID.INPUT=JSON")
    parser.add_argument("--output-node", action="append", default=[])
    parser.add_argument("--timeout", type=int, default=3600)
    parser.add_argument("--poll-seconds", type=float, default=3)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/video"))
    args = parser.parse_args()
    if args.timeout < 30 or args.timeout > 86400 or args.poll_seconds < 0.5 or args.poll_seconds > 60:
        raise ValueError("timeout must be 30-86400 and poll-seconds 0.5-60.")
    if not args.comfy_url.startswith(("http://127.0.0.1", "http://localhost", "http://[::1]", "https://")):
        raise ValueError("Use HTTPS or a loopback ComfyUI address; do not expose an unauthenticated remote ComfyUI service.")
    print(json.dumps(generate(args), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
