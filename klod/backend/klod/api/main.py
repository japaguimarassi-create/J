from __future__ import annotations

import hmac
import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from klod.api.runtime import ModelRuntime, ModelUnavailable
from klod.agent import KlodAgent, KlodContext
from klod.auth.google import InvalidGoogleIdentity, verify_google_identity
from klod.auth.store import AuthStore
from klod.tools.workspace import WorkspacePermissionError, CoderWorkspace

runtime = ModelRuntime()
workspace = CoderWorkspace(os.getenv("KLOD_WORKSPACE_ROOT", "workspaces"))
klod_agent = KlodAgent(runtime, workspace)


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        runtime.load()
    except (ModelUnavailable, FileNotFoundError, KeyError, ValueError, RuntimeError):
        pass
    yield


app = FastAPI(title="Klod API", version="0.3.0", lifespan=lifespan)
origins = [item.strip() for item in os.getenv("KLOD_CORS_ORIGINS", "http://localhost:5173").split(",") if item.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["Content-Type", "Authorization", "X-Klod-CSRF"],
)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    conversation_id: uuid.UUID | None = None
    max_new_tokens: int = Field(default=128, ge=1, le=512)
    temperature: float = Field(default=0.8, gt=0.0, le=2.0)


class GoogleLoginRequest(BaseModel):
    credential: str = Field(min_length=20, max_length=10000)


class ConversationCreate(BaseModel):
    title: str = Field(default="Nova conversa", min_length=1, max_length=160)


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=1000)


class ProjectFileWrite(BaseModel):
    path: str = Field(min_length=1, max_length=240)
    content: str = Field(max_length=1_000_000)


def auth_store() -> AuthStore:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise HTTPException(status_code=503, detail="Google login is not configured: DATABASE_URL is missing")
    try:
        return AuthStore(database_url)
    except (ImportError, RuntimeError, ValueError) as error:
        raise HTTPException(status_code=503, detail="Authentication storage is unavailable") from error


def cookie_settings() -> tuple[str, str, bool, str]:
    session_name = os.getenv("KLOD_SESSION_COOKIE_NAME", "klod_session")
    csrf_name = "klod_csrf"
    secure = os.getenv("KLOD_SESSION_COOKIE_SECURE", "true").lower() in {"1", "true", "yes"}
    same_site = os.getenv("KLOD_COOKIE_SAMESITE", "lax").lower()
    if same_site not in {"lax", "strict", "none"} or (same_site == "none" and not secure):
        raise HTTPException(status_code=503, detail="Session cookie settings are invalid")
    return session_name, csrf_name, secure, same_site


def current_session(request: Request) -> tuple[AuthStore, dict]:
    session_name, _, _, _ = cookie_settings()
    session_token = request.cookies.get(session_name)
    if not session_token:
        raise HTTPException(status_code=401, detail="Authentication required")
    store = auth_store()
    try:
        session = store.get_session(session_token)
    except Exception as error:
        raise HTTPException(status_code=503, detail="Session storage is unavailable") from error
    if session is None:
        raise HTTPException(status_code=401, detail="Session is invalid or expired")
    return store, session


def verify_csrf(request: Request, session: dict, csrf_header: str | None) -> None:
    csrf_cookie = request.cookies.get("klod_csrf", "")
    if not csrf_header or not csrf_cookie or not hmac.compare_digest(csrf_header, csrf_cookie):
        raise HTTPException(status_code=403, detail="CSRF validation failed")
    if not hmac.compare_digest(AuthStore.digest(csrf_header), session["csrf_hash"]):
        raise HTTPException(status_code=403, detail="CSRF validation failed")


def require_admin(session: dict) -> None:
    if session["role"] != "admin":
        raise HTTPException(status_code=403, detail="Administrator permission required")


def project_context(session: dict, project_id: uuid.UUID) -> KlodContext:
    return KlodContext(
        user_id=str(session["id"]),
        permissions=frozenset({"filesystem:read", "filesystem:write"}),
        approved_operations=frozenset(),
        metadata={"workspace_id": str(project_id)},
    )


@app.get("/health")
def health() -> dict[str, str | bool]:
    available = runtime.model is not None and runtime.tokenizer is not None
    return {"service": "klod-api", "ok": True, "model_available": available}


@app.get("/v1/model")
def model_status() -> dict[str, str | bool | int]:
    available = runtime.model is not None and runtime.tokenizer is not None
    return {
        "name": "Klod",
        "available": available,
        "training_steps": runtime.training_steps,
        "parameter_count": runtime.parameter_count,
        "quality_status": "experimental" if available else "not-trained-or-not-configured",
    }


@app.post("/v1/auth/google")
def google_login(payload: GoogleLoginRequest, response: Response) -> dict:
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    if not client_id:
        raise HTTPException(status_code=503, detail="Google OAuth is not configured: GOOGLE_CLIENT_ID is missing")
    try:
        identity = verify_google_identity(payload.credential, client_id)
    except InvalidGoogleIdentity as error:
        raise HTTPException(status_code=401, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail="Google identity verification is unavailable") from error
    store = auth_store()
    try:
        session = store.create_session(identity)
    except Exception as error:
        raise HTTPException(status_code=503, detail="Could not create a secure user session") from error
    session_name, csrf_name, secure, same_site = cookie_settings()
    max_age = 14 * 24 * 60 * 60
    response.set_cookie(session_name, session["session_token"], max_age=max_age, httponly=True, secure=secure, samesite=same_site, path="/")
    response.set_cookie(csrf_name, session["csrf_token"], max_age=max_age, httponly=False, secure=secure, samesite=same_site, path="/")
    return {"user": session["user"], "csrf_token": session["csrf_token"], "expires_at": session["expires_at"].isoformat()}


@app.get("/v1/auth/me")
def auth_me(request: Request) -> dict:
    _, session = current_session(request)
    return {
        "user": {
            "id": session["id"],
            "email": session["email"],
            "display_name": session["display_name"],
            "picture": session["picture"],
            "role": session["role"],
        }
    }


@app.post("/v1/auth/logout")
def auth_logout(
    request: Request,
    response: Response,
    csrf_header: str | None = Header(default=None, alias="X-Klod-CSRF"),
) -> dict[str, bool]:
    store, session = current_session(request)
    session_name, csrf_name, secure, same_site = cookie_settings()
    verify_csrf(request, session, csrf_header)
    try:
        store.revoke_session(request.cookies[session_name])
    except Exception as error:
        raise HTTPException(status_code=503, detail="Could not revoke session") from error
    response.delete_cookie(session_name, path="/", secure=secure, httponly=True, samesite=same_site)
    response.delete_cookie(csrf_name, path="/", secure=secure, httponly=False, samesite=same_site)
    return {"ok": True}


@app.get("/v1/conversations")
def list_conversations(request: Request, limit: int = Query(default=100, ge=1, le=200)) -> dict:
    store, session = current_session(request)
    try:
        return {"conversations": store.list_conversations(session["id"], limit)}
    except Exception as error:
        raise HTTPException(status_code=503, detail="Conversation storage is unavailable") from error


@app.post("/v1/conversations")
def create_conversation(
    payload: ConversationCreate,
    request: Request,
    csrf_header: str | None = Header(default=None, alias="X-Klod-CSRF"),
) -> dict:
    store, session = current_session(request)
    verify_csrf(request, session, csrf_header)
    try:
        return {"conversation": store.create_conversation(session["id"], payload.title)}
    except Exception as error:
        raise HTTPException(status_code=503, detail="Could not create conversation") from error


@app.get("/v1/conversations/{conversation_id}")
def get_conversation(conversation_id: uuid.UUID, request: Request) -> dict:
    store, session = current_session(request)
    try:
        conversation = store.get_conversation(session["id"], str(conversation_id))
    except Exception as error:
        raise HTTPException(status_code=503, detail="Conversation storage is unavailable") from error
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"conversation": conversation}


@app.get("/v1/projects")
def list_projects(request: Request, limit: int = Query(default=100, ge=1, le=200)) -> dict:
    store, session = current_session(request)
    try:
        return {"projects": store.list_projects(session["id"], limit)}
    except Exception as error:
        raise HTTPException(status_code=503, detail="Project storage is unavailable") from error


@app.post("/v1/projects")
def create_project(
    payload: ProjectCreate,
    request: Request,
    csrf_header: str | None = Header(default=None, alias="X-Klod-CSRF"),
) -> dict:
    store, session = current_session(request)
    verify_csrf(request, session, csrf_header)
    try:
        project = store.create_project(session["id"], payload.name, payload.description)
    except Exception as error:
        if error.__class__.__name__ == "UniqueViolation":
            raise HTTPException(status_code=409, detail="A project with this name already exists") from error
        raise HTTPException(status_code=503, detail="Could not create project") from error
    return {"project": project}


@app.get("/v1/projects/{project_id}/files")
def list_or_read_project_file(
    project_id: uuid.UUID,
    request: Request,
    path: str | None = Query(default=None, max_length=240),
) -> dict:
    store, session = current_session(request)
    try:
        project = store.get_project(session["id"], str(project_id))
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        context = project_context(session, project_id)
        if path:
            return {"path": path, "content": klod_agent.read_project_file(path, context)}
        return {"files": klod_agent.list_project_files(context)}
    except (ValueError, WorkspacePermissionError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Project file not found") from error
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=503, detail="Project workspace is unavailable") from error


@app.put("/v1/projects/{project_id}/files")
def write_project_file(
    project_id: uuid.UUID,
    payload: ProjectFileWrite,
    request: Request,
    csrf_header: str | None = Header(default=None, alias="X-Klod-CSRF"),
) -> dict[str, bool | str]:
    store, session = current_session(request)
    verify_csrf(request, session, csrf_header)
    try:
        project = store.get_project(session["id"], str(project_id))
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        context = project_context(session, project_id)
        approved = KlodContext(
            user_id=context.user_id,
            permissions=context.permissions,
            approved_operations=frozenset({"filesystem:write:" + payload.path}),
            metadata=context.metadata,
        )
        klod_agent.write_project_file(payload.path, payload.content, approved)
        return {"ok": True, "path": payload.path}
    except (ValueError, WorkspacePermissionError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=503, detail="Project file could not be saved") from error


@app.get("/v1/admin/overview")
def admin_overview(request: Request) -> dict:
    store, session = current_session(request)
    require_admin(session)
    try:
        return store.admin_overview()
    except Exception as error:
        raise HTTPException(status_code=503, detail="Admin overview is unavailable") from error


@app.get("/v1/admin/users")
def admin_users(request: Request, limit: int = Query(default=100, ge=1, le=200)) -> dict:
    store, session = current_session(request)
    require_admin(session)
    try:
        return {"users": store.list_users(limit)}
    except Exception as error:
        raise HTTPException(status_code=503, detail="User directory is unavailable") from error


@app.post("/v1/chat")
def chat(
    payload: ChatRequest,
    http_request: Request,
    csrf_header: str | None = Header(default=None, alias="X-Klod-CSRF"),
) -> dict[str, str | int]:
    store, session = current_session(http_request)
    verify_csrf(http_request, session, csrf_header)
    try:
        agent_response = klod_agent.respond(payload.message, payload.max_new_tokens, payload.temperature)
        conversation_id = store.save_chat_turn(
            session["id"],
            str(payload.conversation_id) if payload.conversation_id else None,
            payload.message,
            agent_response.text,
        )
    except ModelUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=500, detail="Model inference or conversation persistence failed") from error
    except Exception as error:
        raise HTTPException(status_code=503, detail="Conversation persistence is unavailable") from error
    return {
        "response": agent_response.text,
        "conversation_id": conversation_id,
        "model": "Klod experimental",
        "training_steps": runtime.training_steps,
        "parameter_count": runtime.parameter_count,
    }
