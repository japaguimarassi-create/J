#!/usr/bin/env python3
"""Local-only AOC Migration Center with an encrypted AES-256-GCM vault."""
import base64
import hashlib
import json
import os
import secrets
import shutil
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
except ImportError:
    print("Dependência ausente. Execute: python -m pip install -r requirements.txt", file=sys.stderr)
    raise

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
HOST = "127.0.0.1"
PORT = int(os.environ.get("AOC_CENTER_PORT", "8765"))
CHUNK = 4 * 1024 * 1024
FORMAT = 1
SCRYPT_N = 2**15
SCRYPT_R = 8
SCRYPT_P = 1
LOCK = threading.Lock()


def derive_key(password: str, salt: bytes) -> bytes:
    if len(password) < 12:
        raise ValueError("Use uma senha com pelo menos 12 caracteres.")
    return Scrypt(salt=salt, length=32, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P).derive(password.encode("utf-8"))


def digest_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while True:
            block = stream.read(CHUNK)
            if not block:
                break
            digest.update(block)
            size += len(block)
    return digest.hexdigest(), size


def walk_files(source: Path, errors: list):
    for current, dirs, names in os.walk(source, topdown=True, followlinks=False,
                                         onerror=lambda e: errors.append({"path": str(e.filename or source), "error": str(e)})):
        base = Path(current)
        dirs[:] = [d for d in dirs if not (base / d).is_symlink()]
        for name in names:
            item = base / name
            try:
                if item.is_file() and not item.is_symlink():
                    yield item
            except OSError as exc:
                errors.append({"path": str(item), "error": str(exc)})


def collect(source_strings: list[str], destination: Path | None = None):
    if not source_strings:
        source_strings = [str(Path.home())]
    sources = []
    for raw in source_strings:
        path = Path(raw).expanduser().resolve(strict=True)
        if not path.is_dir() or path == Path(path.anchor):
            raise ValueError("Selecione pastas válidas; não selecione a raiz de uma unidade.")
        if destination and (destination == path or path in destination.parents or destination in path.parents):
            raise ValueError("Origem e destino não podem conter um ao outro.")
        if path not in sources:
            sources.append(path)
    entries, errors, total = [], [], 0
    for index, source in enumerate(sources):
        root_errors = []
        for item in walk_files(source, root_errors):
            try:
                stat = item.stat()
                rel = item.relative_to(source).as_posix()
                entries.append((index, item, rel, stat.st_size, stat.st_mtime_ns))
                total += stat.st_size
            except OSError as exc:
                errors.append({"path": str(item), "error": str(exc)})
        errors.extend(root_errors)
    return sources, entries, errors, total


def encrypt_stream(source: Path, target: Path, key: bytes, aad: bytes):
    nonce = secrets.token_bytes(12)
    encryptor = Cipher(algorithms.AES(key), modes.GCM(nonce)).encryptor()
    encryptor.authenticate_additional_data(aad)
    digest = hashlib.sha256()
    size = 0
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".partial")
    try:
        with source.open("rb") as src, temporary.open("wb") as dst:
            dst.write(nonce)
            while True:
                block = src.read(CHUNK)
                if not block:
                    break
                digest.update(block)
                size += len(block)
                encrypted = encryptor.update(block)
                if encrypted:
                    dst.write(encrypted)
            dst.write(encryptor.finalize())
            dst.write(encryptor.tag)
            dst.flush()
            os.fsync(dst.fileno())
        os.replace(temporary, target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return digest.hexdigest(), size


def verify_stream(path: Path, key: bytes, aad: bytes, expected_hash: str, expected_size: int):
    with path.open("rb") as stream:
        nonce = stream.read(12)
        stream.seek(0, os.SEEK_END)
        length = stream.tell()
        if len(nonce) != 12 or length < 28:
            raise ValueError("Arquivo criptografado truncado.")
        stream.seek(length - 16)
        tag = stream.read(16)
        stream.seek(12)
        remaining = length - 28
        decryptor = Cipher(algorithms.AES(key), modes.GCM(nonce, tag)).decryptor()
        decryptor.authenticate_additional_data(aad)
        digest = hashlib.sha256()
        size = 0
        while remaining:
            block = stream.read(min(CHUNK, remaining))
            if not block:
                raise ValueError("Arquivo criptografado incompleto.")
            remaining -= len(block)
            plain = decryptor.update(block)
            digest.update(plain)
            size += len(plain)
        tail = decryptor.finalize()
        digest.update(tail)
        size += len(tail)
    if size != expected_size or digest.hexdigest() != expected_hash:
        raise ValueError("SHA-256 ou tamanho não corresponde.")
    return True


def encrypt_manifest(manifest: dict, key: bytes, path: Path):
    nonce = secrets.token_bytes(12)
    cipher = Cipher(algorithms.AES(key), modes.GCM(nonce)).encryptor()
    cipher.authenticate_additional_data(b"AOC-MIGRATION-MANIFEST-v1")
    raw = json.dumps(manifest, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    encrypted = cipher.update(raw) + cipher.finalize()
    temp = path.with_suffix(".partial")
    temp.write_bytes(nonce + encrypted + cipher.tag)
    os.replace(temp, path)


def decrypt_manifest(path: Path, key: bytes):
    raw = path.read_bytes()
    if len(raw) < 28:
        raise ValueError("Manifesto criptografado inválido.")
    nonce, tag, ciphertext = raw[:12], raw[-16:], raw[12:-16]
    cipher = Cipher(algorithms.AES(key), modes.GCM(nonce, tag)).decryptor()
    cipher.authenticate_additional_data(b"AOC-MIGRATION-MANIFEST-v1")
    return json.loads(cipher.update(ciphertext) + cipher.finalize())


def vault_open(vault: Path, password: str):
    metadata = json.loads((vault / "vault.json").read_text(encoding="utf-8"))
    if metadata.get("format") != FORMAT or metadata.get("cipher") != "AES-256-GCM":
        raise ValueError("Formato de cofre não suportado.")
    salt = base64.b64decode(metadata["salt"])
    key = derive_key(password, salt)
    manifest = decrypt_manifest(vault / "manifest.enc", key)
    return key, manifest


def do_backup(sources_input: list[str], destination_input: str, password: str):
    destination = Path(destination_input).expanduser().resolve(strict=False)
    sources, entries, scan_errors, total = collect(sources_input, destination)
    if scan_errors:
        raise ValueError("A varredura inicial encontrou erros. Corrija as permissões antes do backup: " + str(scan_errors[:5]))
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("A pasta de destino não está vazia. Escolha uma pasta nova.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(destination.parent).free < total + max(64 * 1024 * 1024, total // 20):
        raise ValueError("Espaço livre insuficiente para o backup e a margem de segurança.")
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "objects").mkdir()
    salt = secrets.token_bytes(16)
    key = derive_key(password, salt)
    metadata = {"format": FORMAT, "cipher": "AES-256-GCM", "kdf": "scrypt", "scrypt_n": SCRYPT_N,
                "scrypt_r": SCRYPT_R, "scrypt_p": SCRYPT_P, "salt": base64.b64encode(salt).decode(),
                "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    (destination / "vault.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    records, errors, done = [], [], 0
    for idx, (root_index, source_file, relative, expected_size, modified_ns) in enumerate(entries):
        object_id = f"{idx:08d}.bin"
        object_path = destination / "objects" / object_id
        aad = ("AOC-MIGRATION-FILE-v1:" + object_id).encode()
        success = False
        for attempt in range(3):
            try:
                before_hash, before_size = digest_file(source_file)
                if before_size != expected_size:
                    expected_size = before_size
                encrypted_hash, copied_size = encrypt_stream(source_file, object_path, key, aad)
                if copied_size != expected_size or encrypted_hash != before_hash:
                    raise ValueError("O arquivo mudou durante a cópia.")
                verify_stream(object_path, key, aad, before_hash, before_size)
                after_hash, after_size = digest_file(source_file)
                if after_hash != before_hash or after_size != before_size:
                    raise ValueError("A origem mudou durante a verificação.")
                records.append({"id": object_id, "root": root_index, "path": relative,
                                "size": before_size, "sha256": before_hash, "modified_ns": modified_ns})
                done += before_size
                success = True
                break
            except Exception as exc:
                object_path.unlink(missing_ok=True)
                if attempt == 2:
                    errors.append({"path": str(source_file), "error": str(exc)})
        if not success:
            continue
    manifest = {"format": FORMAT, "roots": [str(p) for p in sources], "files": records,
                "errors": errors, "source_file_count": len(entries), "source_bytes": total,
                "completed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    encrypt_manifest(manifest, key, destination / "manifest.enc")
    # Re-scan source and require the exact same relative-path set before declaring success.
    _, final_entries, final_errors, _ = collect(sources_input, destination)
    expected_set = {(root, rel) for root, _, rel, _, _ in entries}
    final_set = {(root, rel) for root, _, rel, _, _ in final_entries}
    if final_errors or expected_set != final_set:
        manifest["errors"].append({"path": "source-rescan", "error": "A lista de arquivos mudou ou a nova varredura falhou."})
        encrypt_manifest(manifest, key, destination / "manifest.enc")
    verified = 0
    for record in records:
        try:
            verify_stream(destination / "objects" / record["id"], key,
                          ("AOC-MIGRATION-FILE-v1:" + record["id"]).encode(),
                          record["sha256"], record["size"])
            verified += 1
        except Exception as exc:
            errors.append({"path": record["path"], "error": str(exc)})
    manifest["errors"] = errors + manifest["errors"]
    manifest["verified_files"] = verified
    manifest["success"] = (not manifest["errors"] and verified == len(entries) and len(records) == len(entries)
                           and expected_set == final_set and not final_errors)
    encrypt_manifest(manifest, key, destination / "manifest.enc")
    return {"success": manifest["success"], "files_found": len(entries), "files_encrypted": len(records),
            "files_verified": verified, "bytes_found": total, "errors": manifest["errors"][:30],
            "vault": str(destination), "message": "Backup íntegro." if manifest["success"] else "Backup incompleto: não prossiga para a instalação."}


def do_verify(vault_input: str, password: str):
    vault = Path(vault_input).expanduser().resolve(strict=True)
    key, manifest = vault_open(vault, password)
    good, bad = 0, []
    for record in manifest["files"]:
        try:
            verify_stream(vault / "objects" / record["id"], key,
                          ("AOC-MIGRATION-FILE-v1:" + record["id"]).encode(),
                          record["sha256"], record["size"])
            good += 1
        except Exception as exc:
            bad.append({"path": record["path"], "error": str(exc)})
    success = not bad and not manifest.get("errors") and good == manifest.get("source_file_count")
    return {"success": success, "files_verified": good, "files_expected": manifest.get("source_file_count", 0),
            "errors": (manifest.get("errors", []) + bad)[:30],
            "message": "Cofre íntegro." if success else "Verificação reprovada. Não instale o novo sistema."}


class Handler(BaseHTTPRequestHandler):
    server_version = "AOCMigrationCenter/1.0"

    def log_message(self, *_):
        pass

    def _json(self, status: int, data: Any):
        raw = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _body(self):
        if self.headers.get("Origin") not in (None, f"http://127.0.0.1:{PORT}", f"http://localhost:{PORT}"):
            raise ValueError("Origem da requisição não permitida.")
        length = int(self.headers.get("Content-Length", "0"))
        if length > 1024 * 1024:
            raise ValueError("Requisição muito grande.")
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self):
        if self.path == "/api/status":
            self._json(200, {"ready": True, "platform": sys.platform, "home": str(Path.home())})
            return
        path = WEB / ("index.html" if self.path == "/" else self.path.lstrip("/"))
        if not path.resolve().is_relative_to(WEB.resolve()) or not path.is_file():
            self.send_error(404)
            return
        raw = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8" if path.suffix == ".html" else "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        try:
            data = self._body()
            if self.path == "/api/scan":
                destination = Path(data.get("destination", "")).expanduser().resolve(strict=False) if data.get("destination") else None
                sources, entries, errors, total = collect(data.get("sources", []), destination)
                self._json(200, {"sources": [str(p) for p in sources], "files": len(entries), "bytes": total, "errors": errors[:30]})
            elif self.path == "/api/backup":
                if not LOCK.acquire(blocking=False):
                    raise ValueError("Outra operação já está em andamento.")
                try:
                    result = do_backup(data.get("sources", []), data["destination"], data["password"])
                finally:
                    LOCK.release()
                self._json(200, result)
            elif self.path == "/api/verify":
                result = do_verify(data["vault"], data["password"])
                self._json(200, result)
            else:
                self._json(404, {"error": "Operação desconhecida."})
        except Exception as exc:
            self._json(400, {"error": str(exc)})


def main():
    if not WEB.is_dir():
        raise SystemExit("Pasta web/ não encontrada.")
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"AOC Migration Center: http://{HOST}:{PORT}")
    print("Agente acessível somente neste computador. Mantenha esta janela aberta.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nAgente encerrado.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
