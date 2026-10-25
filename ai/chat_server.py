import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from model import ForgeStudent
from assistant import LocalAssistant
from research import search_web

ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT = Path(os.getenv("MOTIONFORGE_CHECKPOINT", ROOT / "models" / "motionforge-student.pt"))
PORT = int(os.getenv("MOTIONFORGE_PORT", "8765"))
ALLOWED_ORIGINS = set(filter(None, os.getenv("MOTIONFORGE_ALLOWED_ORIGINS", "http://localhost:4173,http://127.0.0.1:4173,null,https://japaguimarassi-create.github.io").split(",")))


def load_model():
    if not CHECKPOINT.exists():
        return None
    bundle = torch.load(CHECKPOINT, map_location="cpu", weights_only=True)
    model = ForgeStudent()
    model.load_state_dict(bundle["state_dict"])
    model.eval()
    return model


MODEL = load_model()
ASSISTANT = LocalAssistant()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(fmt % args)

    def headers(self, status=200, origin=None):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store")
        if origin in ALLOWED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.end_headers()

    def do_OPTIONS(self):
        self.headers(204, self.headers_get("Origin"))

    def headers_get(self, key):
        return self.headers.get(key, "")

    def do_GET(self):
        origin = self.headers_get("Origin")
        if self.path != "/health":
            self.headers(404, origin)
            self.wfile.write(b'{"error":"not_found"}')
            return
        self.headers(200, origin)
        self.wfile.write(json.dumps({"ok": True, "checkpoint": MODEL is not None, "parameters": sum(p.numel() for p in MODEL.parameters()) if MODEL else 0}).encode())

    def do_POST(self):
        origin = self.headers_get("Origin")
        if origin and origin not in ALLOWED_ORIGINS:
            self.headers(403)
            self.wfile.write(b'{"error":"origin_not_allowed"}')
            return
        try:
            length = int(self.headers_get("Content-Length") or "0")
            if length < 1 or length > 12000:
                raise ValueError("corpo precisa conter de 1 a 12000 bytes")
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            if self.path == "/research":
                query = str(body.get("query", "")).strip()
                result = {"query": query, "results": search_web(query)}
            elif self.path == "/chat":
                prompt = str(body.get("prompt", "")).strip()
                if not prompt or len(prompt) > 2000:
                    raise ValueError("prompt precisa conter de 1 a 2000 caracteres")
                if MODEL is None:
                    raise RuntimeError("checkpoint ausente; execute python ai/train.py")
                result = ASSISTANT.answer(prompt, model=MODEL)
                result.update({"model": "MotionForge Student", "parameters": sum(p.numel() for p in MODEL.parameters())})
            else:
                self.headers(404, origin)
                self.wfile.write(b'{"error":"not_found"}')
                return
            self.headers(200, origin)
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))
        except (ValueError, json.JSONDecodeError) as exc:
            self.headers(400, origin)
            self.wfile.write(json.dumps({"error": str(exc)}, ensure_ascii=False).encode("utf-8"))
        except Exception as exc:
            self.headers(503 if self.path == "/chat" else 502, origin)
            self.wfile.write(json.dumps({"error": str(exc)}, ensure_ascii=False).encode("utf-8"))


def main():
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    print("MotionForge local AI at http://127.0.0.1:" + str(PORT))
    server.serve_forever()


if __name__ == "__main__":
    main()
