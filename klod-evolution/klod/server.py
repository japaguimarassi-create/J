import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .code_tools import validate_code
from .memory import ConversationMemory
from .runtime import KlodRuntime
from .shard_runtime import ShardedKlodRuntime
from .tools import analyze_file, create_file

BASE_DIR = Path(__file__).resolve().parent.parent
WORKSPACE = Path(os.getenv("KLOD_WORKSPACE", BASE_DIR / "workspace")).resolve()
DATA_DIR = Path(os.getenv("KLOD_DATA_DIR", BASE_DIR / "runtime_data")).resolve()
CHECKPOINT = os.getenv("KLOD_CHECKPOINT")
SHARD_MANIFEST = Path(os.getenv("KLOD_SHARD_MANIFEST", BASE_DIR / "config" / "shards.json"))
SHARD_CHECKPOINT_DIR = Path(os.getenv("KLOD_SHARD_DIR", BASE_DIR / "runs" / "shards"))
RUNTIME = KlodRuntime(CHECKPOINT) if CHECKPOINT else KlodRuntime()
SHARD_RUNTIME = ShardedKlodRuntime(
    SHARD_MANIFEST,
    SHARD_CHECKPOINT_DIR,
    max_loaded_models=2,
)
MEMORY = ConversationMemory(DATA_DIR / "memory.sqlite3")
app = FastAPI(title="KLOD Evolution", version="0.3.0")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    conversation_id: str = Field(default="default", min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_.-]+$")
    max_new_tokens: int = Field(default=180, ge=1, le=512)


class FileCreateRequest(BaseModel):
    path: str = Field(min_length=1, max_length=240)
    content: str = Field(max_length=2 * 1024 * 1024)
    overwrite: bool = False


class FileAnalyzeRequest(BaseModel):
    path: str = Field(min_length=1, max_length=240)


@app.get("/api/health")
def health():
    shard_status = SHARD_RUNTIME.list_shards()
    trained_shards = [item["id"] for item in shard_status if item["trained"]]
    return {
        "name": "KLOD Evolution",
        "version": "0.3.0",
        "status": "ready",
        "model_trained": RUNTIME.trained or bool(trained_shards),
        "base_model_trained": RUNTIME.trained,
        "trained_shards": trained_shards,
        "workspace": str(WORKSPACE),
        "memory_enabled": True,
    }


@app.get("/api/shards")
def list_shards():
    return {
        "strategy": "independently trained capability models",
        "loaded_shards": list(SHARD_RUNTIME.cache.keys()),
        "shards": SHARD_RUNTIME.list_shards(),
    }


@app.post("/api/chat")
def chat(request: ChatRequest):
    if not RUNTIME.trained and not SHARD_RUNTIME.available:
        raise HTTPException(
            status_code=409,
            detail="Nenhum checkpoint treinado foi encontrado. Execute klod.train ou klod.train_shards.",
        )
    try:
        history = MEMORY.recent(request.conversation_id, limit=8)
        context = "\n".join(
            f"{'Usuário' if item['role'] == 'user' else 'KLOD'}: {item['content']}"
            for item in history
        )
        prompt = f"{context}\nUsuário: {request.message}" if context else request.message

        selected_shard = None
        selected_domain = None
        if SHARD_RUNTIME.available:
            result = SHARD_RUNTIME.chat_with_metadata(prompt, request.max_new_tokens)
            response = result["response"]
            selected_shard = result["shard_id"]
            selected_domain = result["domain"]
        else:
            response = RUNTIME.chat(prompt, request.max_new_tokens)

        MEMORY.add(request.conversation_id, "user", request.message)
        MEMORY.add(request.conversation_id, "assistant", response)
        return {
            "response": response,
            "conversation_id": request.conversation_id,
            "memory_messages_used": len(history),
            "shard_id": selected_shard,
            "shard_domain": selected_domain,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Generation failed: {type(exc).__name__}: {exc}",
        ) from exc


@app.get("/api/conversations/{conversation_id}")
def conversation_history(conversation_id: str):
    if not conversation_id or len(conversation_id) > 80:
        raise HTTPException(status_code=400, detail="Invalid conversation ID")
    return {"conversation_id": conversation_id, "messages": MEMORY.recent(conversation_id, limit=40)}


@app.delete("/api/conversations/{conversation_id}")
def clear_conversation(conversation_id: str):
    if not conversation_id or len(conversation_id) > 80:
        raise HTTPException(status_code=400, detail="Invalid conversation ID")
    return {"conversation_id": conversation_id, "deleted_messages": MEMORY.clear(conversation_id)}


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


@app.post("/api/code/validate")
def code_validate(request: FileAnalyzeRequest):
    try:
        return validate_code(WORKSPACE, request.path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="File not found in workspace") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=415, detail="File is not valid UTF-8 text") from exc


@app.get("/")
def home():
    return FileResponse(BASE_DIR / "web" / "index.html")
