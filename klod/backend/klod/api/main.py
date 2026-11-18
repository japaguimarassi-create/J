from __future__ import annotations

import hmac
import os
import re
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from argon2 import PasswordHasher, exceptions as argon2_errors

from klod.api.runtime import ModelRuntime, ModelUnavailable
from klod.agent import KlodAgent, KlodContext
from klod.auth.google import InvalidGoogleIdentity, verify_google_identity
from klod.auth import email as email_service
from klod.auth.store import AuthStore
from klod.tools.workspace import WorkspacePermissionError, CoderWorkspace

runtime = ModelRuntime()
workspace = CoderWorkspace(os.getenv("KLOD_WORKSPACE_ROOT", "workspaces"))
klod_agent = KlodAgent(runtime, workspace)
password_hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)


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


class EmailPayload(BaseModel):
    email: str = Field(min_length=5, max_length=254)

    @field_validator("email")
    @classmethod
    def normalise_email(cls, value: str) -> str:
        email = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            raise ValueError("Informe um endereço de e-mail válido.")
        return email


class RegisterRequest(EmailPayload):
    display_name: str = Field(min_length=1, max_length=160)
    password: str = Field(min_length=10, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_bytes(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 128:
            raise ValueError("A senha deve ter no máximo 128 bytes.")
        return value


class LoginRequest(EmailPayload):
    password: str = Field(min_length=1, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_bytes(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 128:
            raise ValueError("A senha deve ter no máximo 128 bytes.")
        return value


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=20, max_length=128)
    password: str = Field(min_length=10, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_bytes(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 128:
            raise ValueError("A senha deve ter no máximo 128 bytes.")
        return value


class EmailTokenRequest(BaseModel):
    token: str = Field(min_length=20, max_length=128)


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


def set_auth_cookies(response: Response, session: dict) -> None:
    session_name, csrf_name, secure, same_site = cookie_settings()
    max_age = 14 * 24 * 60 * 60
    response.set_cookie(session_name, session["session_token"], max_age=max_age, httponly=True, secure=secure, samesite=same_site, path="/")
    response.set_cookie(csrf_name, session["csrf_token"], max_age=max_age, httponly=False, secure=secure, samesite=same_site, path="/")


def email_action_url(token: str, action: str) -> str:
    app_url = os.getenv("KLOD_APP_URL", "").strip().rstrip("/")
    if not app_url.startswith("https://") and not app_url.startswith("http://localhost"):
        raise HTTPException(status_code=503, detail="KLOD_APP_URL deve apontar para o endereço HTTPS do aplicativo.")
    if not email_service.is_configured():
        raise HTTPException(status_code=503, detail="O envio de e-mails ainda não foi configurado no servidor.")
    return f"{app_url}/?{action}={token}"


def send_account_email(email: str, token: str, purpose: str) -> None:
    action = "verify" if purpose == "verify_email" else "reset"
    link = email_action_url(token, action)
    if purpose == "verify_email":
        subject = "Confirme seu e-mail para acessar o Klod"
        text_body = f"Olá! Confirme seu endereço de e-mail para ativar sua conta Klod:\n\n{link}\n\nO link expira em 30 minutos e só pode ser usado uma vez. Se você não solicitou esta conta, ignore esta mensagem."
        heading = "Confirme seu e-mail"
        button = "Ativar minha conta"
    else:
        subject = "Redefina sua senha do Klod"
        text_body = f"Recebemos uma solicitação para redefinir sua senha Klod:\n\n{link}\n\nO link expira em 30 minutos e só pode ser usado uma vez. Se você não solicitou a redefinição, ignore esta mensagem."
        heading = "Redefina sua senha"
        button = "Criar nova senha"
    html_body = (
        "<div style='margin:0;padding:36px 16px;background:#0b1117;font-family:Arial,sans-serif;color:#eaf3f1'>"
        "<div style='max-width:520px;margin:auto;padding:32px;border:1px solid #263b40;border-radius:20px;background:#121d24'>"
        "<div style='font-size:13px;font-weight:800;letter-spacing:4px;color:#7de6d0'>KLOD</div>"
        f"<h1 style='font-size:25px;line-height:1.2;margin:28px 0 12px'>{heading}</h1>"
        "<p style='font-size:15px;line-height:1.7;color:#a9bcba'>Use o botão abaixo para continuar com segurança. Este link expira em 30 minutos.</p>"
        f"<p style='margin:28px 0'><a href='{link}' style='display:inline-block;padding:15px 22px;border-radius:12px;background:#7de6d0;color:#071512;text-decoration:none;font-weight:700'>{button}</a></p>"
        "<p style='font-size:12px;line-height:1.6;color:#809492'>Se você não fez esta solicitação, pode ignorar esta mensagem.</p>"
        "</div></div>"
    )
    try:
        email_service.send_action_email(email, subject, text_body, html_body)
    except email_service.EmailDeliveryError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


def auth_store() -> AuthStore:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise HTTPException(status_code=503, detail="A autenticação não está configurada: DATABASE_URL está ausente")
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


@app.post("/v1/auth/register")
def register(payload: RegisterRequest) -> dict[str, str]:
    store = auth_store()
    try:
        user = store.create_email_account(
            payload.email,
            payload.display_name,
            password_hasher.hash(payload.password),
        )
        if user:
            token = store.issue_email_token(user["id"], "verify_email")
            send_account_email(payload.email, token, "verify_email")
        else:
            existing = store.get_auth_user(payload.email)
            if existing and not existing["email_verified"]:
                token = store.issue_email_token(existing["id"], "verify_email")
                send_account_email(payload.email, token, "verify_email")
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=503, detail="Não foi possível concluir o cadastro. Tente novamente.") from error
    return {"message": "Se o endereço puder receber uma confirmação, enviaremos um link para ativar a conta."}


@app.post("/v1/auth/login")
def email_login(payload: LoginRequest, request: Request, response: Response) -> dict:
    store = auth_store()
    remote = request.client.host if request.client else "unknown"
    attempt_key = payload.email + ":" + remote
    try:
        if store.is_login_rate_limited(attempt_key):
            raise HTTPException(status_code=429, detail="Muitas tentativas. Aguarde 15 minutos e tente novamente.")
        user = store.get_auth_user(payload.email)
        valid_password = False
        if user and user["password_hash"]:
            try:
                valid_password = password_hasher.verify(user["password_hash"], payload.password)
            except (argon2_errors.VerifyMismatchError, argon2_errors.VerificationError, argon2_errors.InvalidHashError):
                valid_password = False
        if not valid_password:
            store.record_login_failure(attempt_key)
            raise HTTPException(status_code=401, detail="E-mail ou senha incorretos.")
        if not user["email_verified"]:
            raise HTTPException(status_code=403, detail="Confirme seu e-mail antes de entrar. Confira também a pasta de spam.")
        store.clear_login_failures(attempt_key)
        session = store.create_session_for_user(user["id"])
        if session is None:
            raise HTTPException(status_code=401, detail="Não foi possível iniciar a sessão. Entre novamente.")
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=503, detail="O serviço de autenticação está indisponível.") from error
    set_auth_cookies(response, session)
    return {"user": session["user"], "expires_at": session["expires_at"].isoformat()}


@app.post("/v1/auth/verify-email")
def verify_email(payload: EmailTokenRequest, response: Response) -> dict:
    store = auth_store()
    try:
        identity = store.consume_email_token(
            payload.token,
            "verify_email",
            owner_email=os.getenv("KLOD_OWNER_EMAIL", ""),
        )
        if identity is None:
            raise HTTPException(status_code=400, detail="Este link é inválido, já foi usado ou expirou. Solicite outro.")
        session = store.create_session_for_user(identity["id"])
        if session is None:
            raise HTTPException(status_code=503, detail="A conta foi confirmada, mas não foi possível iniciar a sessão.")
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=503, detail="Não foi possível confirmar o endereço de e-mail.") from error
    set_auth_cookies(response, session)
    return {"user": session["user"]}


@app.post("/v1/auth/resend-verification")
def resend_verification(payload: EmailPayload) -> dict[str, str]:
    store = auth_store()
    try:
        user = store.get_auth_user(payload.email)
        if user and not user["email_verified"]:
            token = store.issue_email_token(user["id"], "verify_email")
            send_account_email(payload.email, token, "verify_email")
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=503, detail="Não foi possível solicitar um novo e-mail.") from error
    return {"message": "Se houver uma conta pendente para este endereço, enviaremos um novo link de confirmação."}


@app.post("/v1/auth/forgot-password")
def forgot_password(payload: EmailPayload) -> dict[str, str]:
    if not email_service.is_configured() or not os.getenv("KLOD_APP_URL", "").strip():
        raise HTTPException(status_code=503, detail="O serviço de e-mail ainda não está configurado.")
    store = auth_store()
    try:
        user = store.get_auth_user(payload.email)
        if user:
            token = store.issue_email_token(user["id"], "reset_password")
            send_account_email(payload.email, token, "reset_password")
    except HTTPException:
        raise
    except Exception:
        pass
    return {"message": "Se existir uma conta associada ao endereço, enviaremos instruções para redefinir a senha."}


@app.post("/v1/auth/reset-password")
def reset_password(payload: ResetPasswordRequest) -> dict[str, str]:
    store = auth_store()
    try:
        identity = store.consume_email_token(
            payload.token,
            "reset_password",
            new_password_hash=password_hasher.hash(payload.password),
        )
        if identity is None:
            raise HTTPException(status_code=400, detail="Este link é inválido, já foi usado ou expirou. Solicite outro.")
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=503, detail="Não foi possível redefinir a senha.") from error
    return {"message": "Senha atualizada. Entre com sua nova senha."}


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
