from __future__ import annotations

import os
import sqlite3
import uuid
import tempfile
import subprocess
from contextlib import closing
from pathlib import Path
from typing import Literal, Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from socializer.engine import LocalModel
from socializer.game import ModKnowledge, fallback_game_reply

ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("ENTURMA_DB", str(ROOT / "enturma.sqlite3")))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
engine = LocalModel()
mod_knowledge = ModKnowledge()
app = FastAPI(title="Enturma AI", description="Núcleo social e conversacional para o mod Minecraft Enturma")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=8000)
    context: str = Field(default="", max_length=5000)
    goal: str = Field(default="", max_length=1000)
    mode: Literal["conversar", "enturmar"] = "conversar"
    tone: Literal["natural", "casual", "calmo", "direto", "engracado"] = "natural"


class MobTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=1000)


class MinecraftDialogueRequest(BaseModel):
    player_name: str = Field(default="jogador", max_length=80)
    player_message: str = Field(default="Oi", max_length=2000)
    mob_name: str = Field(default="criatura", max_length=100)
    mob_id: str = Field(default="minecraft:villager", max_length=120)
    voice_profile: str = Field(default="generic", max_length=80)
    dimension: str = Field(default="minecraft:overworld", max_length=120)
    game_context: str = Field(default="", max_length=1500)
    installed_mods: list[str] = Field(default_factory=list, max_length=100)
    history: list[MobTurn] = Field(default_factory=list, max_length=8)
    research: bool = True


class ModKnowledgeRequest(BaseModel):
    query: str = Field(min_length=1, max_length=180)
    installed_mods: list[str] = Field(default_factory=list, max_length=100)
    enabled: bool = True


class VoiceRequest(BaseModel):
    text: str = Field(min_length=1, max_length=450)
    profile: str = Field(default="generic", max_length=80)


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_db() -> None:
    with closing(connect()) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                context TEXT NOT NULL DEFAULT '',
                goal TEXT NOT NULL DEFAULT '',
                mode TEXT NOT NULL DEFAULT 'conversar',
                tone TEXT NOT NULL DEFAULT 'natural',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(session_id) REFERENCES sessions(session_id)
            );
            CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id, id);
        """)
        conn.commit()


@app.on_event("startup")
def startup() -> None:
    initialize_db()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"ok": True, "name": "Enturma AI", "model": engine.status(), "minecraft_api": True, "web_mod_research": "optional ddgs package"}


@app.post("/api/chat")
def chat(request: ChatRequest) -> dict[str, Any]:
    user_message = request.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="A mensagem não pode ficar vazia.")
    with closing(connect()) as conn:
        conn.execute(
            "INSERT INTO sessions(session_id, context, goal, mode, tone) VALUES(?, ?, ?, ?, ?) "
            "ON CONFLICT(session_id) DO UPDATE SET context=excluded.context, goal=excluded.goal, mode=excluded.mode, tone=excluded.tone",
            (request.session_id, request.context, request.goal, request.mode, request.tone),
        )
        history_rows = conn.execute(
            "SELECT role, content FROM messages WHERE session_id=? ORDER BY id DESC LIMIT 16",
            (request.session_id,),
        ).fetchall()
        history = [{"role": row["role"], "content": row["content"]} for row in reversed(history_rows)]
        history.append({"role": "user", "content": user_message})
        conn.execute("INSERT INTO messages(session_id, role, content) VALUES(?, 'user', ?)", (request.session_id, user_message))
        conn.commit()
    try:
        answer = engine.reply(history, request.context, request.goal, request.mode, request.tone)
        model_used = True
    except Exception as exc:
        engine.last_error = str(exc)[:500]
        answer = "Não consegui carregar o modelo local agora. Confira memória, dependências e o download inicial dos pesos; sua conversa foi preservada."
        model_used = False
    with closing(connect()) as conn:
        conn.execute("INSERT INTO messages(session_id, role, content) VALUES(?, 'assistant', ?)", (request.session_id, answer))
        conn.commit()
    return {"session_id": request.session_id, "reply": answer, "model_used": model_used}


@app.post("/api/minecraft/dialogue")
def minecraft_dialogue(request: MinecraftDialogueRequest) -> dict[str, Any]:
    payload = request.model_dump()
    payload["history"] = [turn.model_dump() for turn in request.history]
    knowledge = mod_knowledge.lookup(request.player_message, request.installed_mods, request.research)
    try:
        result = engine.reply_mob(payload, knowledge)
        result["model_used"] = True
        result["research_used"] = bool(knowledge)
        return result
    except Exception as exc:
        engine.last_error = str(exc)[:500]
        result = fallback_game_reply(payload)
        result["model_used"] = False
        result["research_used"] = bool(knowledge)
        result["reason"] = "Modelo local indisponível; resposta de contingência aplicada."
        return result


@app.post("/api/minecraft/mod-knowledge")
def minecraft_mod_knowledge(request: ModKnowledgeRequest) -> dict[str, Any]:
    result = mod_knowledge.lookup(request.query, request.installed_mods, request.enabled)
    return {"query": request.query, "found": bool(result), "knowledge": result, "source": "busca web leve opcional" if result else "sem resultados; pacote ddgs não instalado ou pesquisa sem correspondência"}


@app.post("/api/minecraft/voice")
async def minecraft_voice(request: VoiceRequest) -> Response:
    try:
        import edge_tts
    except ImportError as exc:
        raise HTTPException(status_code=501, detail="Voz opcional indisponível: instale requirements-voice.txt.") from exc
    from socializer.game import VOICE_PROFILES
    profile = VOICE_PROFILES.get(request.profile, VOICE_PROFILES["generic"])
    try:
        with tempfile.TemporaryDirectory(prefix="enturma-voice-") as temp_dir:
            mp3_path = str(Path(temp_dir) / "speech.mp3")
            communicate = edge_tts.Communicate(request.text, profile["voice"], rate=profile["rate"], pitch=profile["pitch"])
            await communicate.save(mp3_path)
            decoded = subprocess.run(
                ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-i", mp3_path, "-f", "s16le", "-acodec", "pcm_s16le", "-ar", "48000", "-ac", "1", "pipe:1"],
                check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=25,
            )
            raw_pcm = decoded.stdout[:2880000]
            if not raw_pcm:
                raise RuntimeError("TTS retornou áudio vazio")
            return Response(content=raw_pcm, media_type="application/octet-stream", headers={"X-Audio-Format": "pcm_s16le_48000_mono", "Cache-Control": "no-store"})
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Falha ao gerar voz. Verifique se ffmpeg está instalado e se o serviço de voz pode acessar a internet.") from exc


@app.get("/api/history/{session_id}")
def history(session_id: str) -> dict[str, Any]:
    with closing(connect()) as conn:
        rows = conn.execute("SELECT role, content, created_at FROM messages WHERE session_id=? ORDER BY id ASC LIMIT 200", (session_id,)).fetchall()
    return {"session_id": session_id, "messages": [dict(row) for row in rows]}


@app.delete("/api/history/{session_id}")
def delete_history(session_id: str) -> dict[str, Any]:
    with closing(connect()) as conn:
        conn.execute("DELETE FROM messages WHERE session_id=?", (session_id,))
        conn.execute("DELETE FROM sessions WHERE session_id=?", (session_id,))
        conn.commit()
    return {"deleted": True, "session_id": session_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host=os.getenv("ENTURMA_HOST", "127.0.0.1"), port=int(os.getenv("ENTURMA_PORT", "8000")), reload=False)
