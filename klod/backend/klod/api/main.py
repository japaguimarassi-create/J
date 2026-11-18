from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from klod.api.runtime import ModelRuntime, ModelUnavailable

runtime = ModelRuntime()


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        runtime.load()
    except (ModelUnavailable, FileNotFoundError, KeyError, ValueError, RuntimeError):
        pass
    yield


app = FastAPI(title="Klod API", version="0.1.0", lifespan=lifespan)
origins = [value.strip() for value in os.getenv("KLOD_CORS_ORIGINS", "http://localhost:5173").split(",") if value.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["GET", "POST"], allow_headers=["Content-Type", "Authorization"])


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    max_new_tokens: int = Field(default=128, ge=1, le=512)
    temperature: float = Field(default=0.8, gt=0.0, le=2.0)


@app.get("/health")
def health():
    available = runtime.model is not None and runtime.tokenizer is not None
    return {"service": "klod-api", "ok": True, "model_available": available}


@app.get("/v1/model")
def model_status():
    available = runtime.model is not None and runtime.tokenizer is not None
    return {"name": "Klod", "available": available, "training_steps": runtime.training_steps, "parameter_count": runtime.parameter_count, "quality_status": "experimental" if available else "not-trained-or-not-configured"}


@app.post("/v1/chat")
def chat(request: ChatRequest):
    try:
        response = runtime.generate(request.message, request.max_new_tokens, request.temperature)
    except ModelUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=500, detail="Model inference failed") from error
    return {"response": response, "model": "Klod experimental", "training_steps": runtime.training_steps, "parameter_count": runtime.parameter_count}
