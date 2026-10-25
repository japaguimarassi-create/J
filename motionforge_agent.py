from __future__ import annotations

import json
import os
import secrets
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
DEFAULT_TEACHERS = ["qwen3.6:27b", "gemma4:12b", "gpt-oss:20b"]
ESTIMATED_MODEL_GB = {"qwen3.6:27b": 19, "gemma4:12b": 8, "gpt-oss:20b": 14}
STARTUP_TIMEOUT_SECONDS = 120


def endpoint_parts(base_url: str) -> tuple[str, str, str, int]:
    parsed = urllib.parse.urlparse(base_url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("OLLAMA_BASE_URL precisa ser um endereço HTTP ou HTTPS válido.")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    cli_host = parsed.hostname if port in (80, 443) else parsed.hostname + ":" + str(port)
    normalized_host = parsed.hostname.casefold()
    local = normalized_host in ("127.0.0.1", "localhost", "::1")
    return parsed.scheme, parsed.hostname, cli_host, port if local else port


def http_json(url: str, timeout: float = 3.0) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        value = json.loads(response.read().decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("A resposta do serviço Ollama não é um objeto JSON.")
    return value


def ollama_tags(base_url: str) -> list[str]:
    value = http_json(base_url.rstrip("/") + "/api/tags")
    return [
        str(item.get("name", "")).strip()
        for item in value.get("models", [])
        if isinstance(item, dict) and item.get("name")
    ]


def model_present(model: str, installed: list[str]) -> bool:
    requested = model.strip()
    return any(name == requested for name in installed)


def model_list() -> list[str]:
    configured = [
        item.strip()
        for item in os.environ.get("MOTIONFORGE_TEACHERS", ",".join(DEFAULT_TEACHERS)).split(",")
        if item.strip()
    ]
    if len(configured) != 3 or len(set(configured)) != 3:
        raise ValueError("MOTIONFORGE_TEACHERS precisa listar exatamente três modelos diferentes.")
    return configured


def local_model_storage() -> Path:
    override = os.environ.get("OLLAMA_MODELS", "").strip()
    return Path(override).expanduser() if override else Path.home() / ".ollama" / "models"


def required_free_gb(models: list[str]) -> int:
    return sum(ESTIMATED_MODEL_GB.get(model, 20) for model in models) + 4


def verify_disk_space(models_to_pull: list[str]) -> None:
    if not models_to_pull:
        return
    path = local_model_storage()
    path.mkdir(parents=True, exist_ok=True)
    free_gb = shutil.disk_usage(path).free / (1024 ** 3)
    needed_gb = required_free_gb(models_to_pull)
    if free_gb < needed_gb:
        raise RuntimeError(
            "Espaço insuficiente para baixar os três professores. "
            f"Disponível: {free_gb:.1f} GB; estimativa necessária para os modelos faltantes: {needed_gb} GB. "
            "Libere espaço ou instale os modelos antes de iniciar o agente."
        )


def wait_for_ollama(base_url: str, timeout: int = STARTUP_TIMEOUT_SECONDS) -> list[str]:
    deadline = time.monotonic() + timeout
    last_error = "sem resposta"
    while time.monotonic() < deadline:
        try:
            return ollama_tags(base_url)
        except Exception as exc:
            last_error = str(exc)
            time.sleep(2)
    raise RuntimeError("Ollama não respondeu em " + base_url + " dentro do prazo. Último erro: " + last_error)


def start_local_ollama(base_url: str) -> subprocess.Popen[bytes] | None:
    scheme, host, cli_host, port = endpoint_parts(base_url)
    if scheme != "http" or host.casefold() not in ("127.0.0.1", "localhost", "::1"):
        return None
    executable = shutil.which("ollama")
    if not executable:
        raise RuntimeError(
            "O comando 'ollama' não foi encontrado. Instale o Ollama na máquina que vai hospedar os três modelos; "
            "o APK Android não consegue iniciar modelos de 12B/20B/27B sozinho."
        )
    env = os.environ.copy()
    env["OLLAMA_HOST"] = cli_host
    return subprocess.Popen([executable, "serve"], cwd=ROOT, env=env)


def pull_missing_models(base_url: str, models: list[str], installed: list[str]) -> list[str]:
    missing = [model for model in models if not model_present(model, installed)]
    if not missing:
        print("Todos os três modelos já estão instalados.")
        return installed
    if os.environ.get("MOTIONFORGE_AUTO_PULL", "1").strip().lower() not in ("1", "true", "yes", "on"):
        raise RuntimeError(
            "Faltam modelos Ollama: " + ", ".join(missing)
            + ". Defina MOTIONFORGE_AUTO_PULL=1 para baixá-los automaticamente."
        )
    scheme, host, cli_host, _ = endpoint_parts(base_url)
    if scheme != "http" or host.casefold() not in ("127.0.0.1", "localhost", "::1"):
        raise RuntimeError(
            "O endpoint Ollama configurado é remoto e faltam modelos: " + ", ".join(missing)
            + ". Execute 'ollama pull NOME' no próprio servidor que hospeda o Ollama, depois reinicie o agente."
        )
    verify_disk_space(missing)
    executable = shutil.which("ollama")
    if not executable:
        raise RuntimeError("O executável Ollama não está instalado nesta máquina.")
    env = os.environ.copy()
    env["OLLAMA_HOST"] = cli_host
    for model in missing:
        print("Baixando " + model + ". Este arquivo pode ocupar dezenas de GB.")
        completed = subprocess.run([executable, "pull", model], cwd=ROOT, env=env, check=False)
        if completed.returncode != 0:
            raise RuntimeError("Falha ao baixar " + model + ". Verifique rede, espaço e saída do Ollama.")
    return ollama_tags(base_url)


def ensure_api_key() -> str:
    key = os.environ.get("MOTIONFORGE_API_KEY", "").strip()
    if key:
        return key
    key = secrets.token_urlsafe(36)
    os.environ["MOTIONFORGE_API_KEY"] = key
    print("\nCHAVE DE ACESSO DO APP (copie-a nas configurações do APK):")
    print(key)
    print("Guarde-a num local privado. Ela será regenerada se o agente reiniciar sem variável de ambiente.")
    return key


def run() -> int:
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    models = model_list()
    os.environ["MOTIONFORGE_TEACHERS"] = ",".join(models)
    os.environ["OLLAMA_BASE_URL"] = base_url
    _, host, _, _ = endpoint_parts(base_url)
    local = host.casefold() in ("127.0.0.1", "localhost", "::1")

    if local:
        try:
            installed = ollama_tags(base_url)
            ollama_process = None
        except Exception:
            ollama_process = start_local_ollama(base_url)
            installed = wait_for_ollama(base_url)
    else:
        ollama_process = None
        installed = wait_for_ollama(base_url)

    installed = pull_missing_models(base_url, models, installed)
    missing = [model for model in models if not model_present(model, installed)]
    if missing:
        raise RuntimeError("Ainda faltam modelos no Ollama: " + ", ".join(missing))

    host_bind = os.environ.get("MOTIONFORGE_HOST", "0.0.0.0").strip()
    os.environ["MOTIONFORGE_HOST"] = host_bind
    if host_bind.casefold() not in ("127.0.0.1", "localhost", "::1"):
        ensure_api_key()
    elif os.environ.get("MOTIONFORGE_API_KEY", "").strip():
        print("API protegida por MOTIONFORGE_API_KEY.")

    port = os.environ.get("PORT", "8000")
    print("\nMotionForge Orchestrator pronto.")
    print("Três modelos disponíveis: " + ", ".join(models))
    print("Backend: http://" + host_bind + ":" + port)
    print("Configure no APK a URL acessível por ele e a chave de acesso mostrada acima.")
    print("O orquestrador chama os modelos sequencialmente e entrega a síntese ao editor.")
    process = subprocess.Popen([sys.executable, str(ROOT / "server.py")], cwd=ROOT, env=os.environ.copy())
    try:
        return process.wait()
    except KeyboardInterrupt:
        process.send_signal(signal.SIGINT)
        return process.wait()
    finally:
        if ollama_process is not None and ollama_process.poll() is None:
            ollama_process.terminate()
            try:
                ollama_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                ollama_process.kill()


def main() -> None:
    try:
        code = run()
    except KeyboardInterrupt:
        code = 130
    except Exception as exc:
        print("MotionForge Orchestrator: " + str(exc), file=sys.stderr)
        code = 1
    raise SystemExit(code)


if __name__ == "__main__":
    main()
