from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Klod API", version="0.1.0")

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=20000)

@app.get("/health")
def health():
    return {"status": "ok", "product": "Klod", "inference_ready": False}

@app.post("/v1/chat")
def chat(request: ChatRequest):
    raise HTTPException(status_code=503, detail="No trained and approved Klod checkpoint is configured.")
