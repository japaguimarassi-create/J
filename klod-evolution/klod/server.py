import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .runtime import KlodRuntime
from .tools import analyze_file, create_file

BASE_DIR = Path(__file__).resolve().parent.parent
WORKSPACE = Path(os.getenv("KLOD_WORKSPACE", BASE_DIR / "workspace")).resolve()
CHECKPOINT = os.getenv("KLOD_CHECKPOINT")
RUNTIME = KlodRuntime(CHECKPOINT) if CHECKPOINT else KlodRuntime()
app = FastAPI(title="KLOD Evolution", version="0.1.0")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    max_new_tokens: int = Field(default=180, ge=1, le=512)


class FileCreateRequest(BaseModel):
    path: str = Field(min_length=1, max_length=240)
    content: str = Field(max_length=2 * 1024 * 1024)
    overwrite: bool = False


class FileAnalyzeRequest(BaseModel):
    path: str = Field(min_length=1, max_length=240)


@app.get("/api/health")
def health():
    return {
        "name": "KLOD Evolution",
        "status": "ready",
        "model_trained": RUNTIME.trained,
        "workspace": str(WORKSPACE),
    }


@app.post("/api/chat")
def chat(request: ChatRequest):
    if not RUNTIME.trained:
        raise HTTPException(
            status_code=409,
            detail="Modelo ainda não treinado. Execute klod.train com um corpus local.",
        )
    try:
        return {"response": RUNTIME.chat(request.message, request.max_new_tokens)}
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Generation failed: {type(exc).__name__}: {exc}",
        ) from exc


@app.post("/api/files/analyze")
def file_analyze(request: FileAnalyzeRequest):
    try:
        return analyze_file(WORKSPACE, request.path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="File not found in workspace") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.post("/api/files/create")
def file_create(request: FileCreateRequest):
    try:
        return create_file(WORKSPACE, request.path, request.content, request.overwrite)
    except FileExistsError as exc:
        raise HTTPException(
            status_code=409,
            detail="File already exists; set overwrite=true explicitly",
        ) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc


@app.get("/")
def home():
    return FileResponse(BASE_DIR / "web" / "index.html")
