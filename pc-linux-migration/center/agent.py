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
        kept = []
        for dirname in dirs:
            candidate = base / dirname
            if candidate.is_symlink():
                errors.append({"path": str(candidate), "error": "Link simbólico ignorado; confira manualmente o destino dos dados."})
            else:
                kept.append(dirname)
        dirs[:] = kept
        for name in names:
            item = base / name
            try:
                if item.is_symlink():
                    errors.append({"path": str(item), "error": "Link simbólico ignorado; confira manualmente o destino dos dados."})
                elif item.is_file():
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
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination_device = os.stat(destination.parent).st_dev
    same_disk = [str(source) for source in sources if os.stat(source).st_dev == destination_device]
    if same_disk:
        raise ValueError("O destino precisa estar em outro disco físico/unidade. Origem e destino estão na mesma unidade: " + ", ".join(same_disk))
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
        errors.append({"path": "source-rescan", "error": "A lista de arquivos mudou ou a nova varredura falhou."})
    final_map = {(root, rel): (path, size, modified) for root, path, rel, size, modified in final_entries}
    for record in records:
        current = final_map.get((record["root"], record["path"]))
        if current is None:
            errors.append({"path": record["path"], "error": "Arquivo desapareceu na segunda varredura."})
            continue
        source_file, _, current_mtime = current
        try:
            current_hash, current_size = digest_file(source_file)
            if current_hash != record["sha256"] or current_size != record["size"]:
                object_path = destination / "objects" / record["id"]
                aad = ("AOC-MIGRATION-FILE-v1:" + record["id"]).encode()
                repaired = False
                for attempt in range(3):
                    before_hash, before_size = digest_file(source_file)
                    encrypt_stream(source_file, object_path, key, aad)
                    verify_stream(object_path, key, aad, before_hash, before_size)
                    after_hash, after_size = digest_file(source_file)
                    if before_hash == after_hash and before_size == after_size:
                        record["sha256"], record["size"] = before_hash, before_size
                        record["modified_ns"] = current_mtime
                        repaired = True
                        break
                if not repaired:
                    raise ValueError("Arquivo continuou mudando durante as tentativas de correção.")
        except Exception as exc:
            errors.append({"path": record["path"], "error": "Falha na auditoria/repetição: " + str(exc)})
    verified = 0
    for record in records:
        try:
            verify_stream(destination / "objects" / record["id"], key,
                          ("AOC-MIGRATION-FILE-v1:" + record["id"]).encode(),
                          record["sha256"], record["size"])
            verified += 1
        except Exception as exc:
            errors.append({"path": record["path"], "error": str(exc)})
    manifest["errors"] = errors
    manifest["verified_files"] = verified
    manifest["success"] = (not manifest["errors"] and verified == len(entries) and len(records) == len(entries)
                           and expected_set == final_set and not final_errors)
    encrypt_manifest(manifest, key, destination / "manifest.enc")
    return {"success": manifest["success"], "files_found": len(entries), "files_encrypted": len(records),
            "files_verified": verified, "bytes_found": total, "errors": manifest["errors"][:30],
            "vault": str(destination), "message": "Backup íntegro." if manifest["success"] else "Backup incompleto: não prossiga para a instalação."}



def decrypt_stream_to_path(vault: Path, record: dict, key: bytes, output: Path):
    object_id = record.get("id")
    if not isinstance(object_id, str) or not object_id.endswith(".bin") or not object_id[:-4].isdigit():
        raise ValueError("Identificador de objeto inválido.")
    encrypted_path = vault / "objects" / object_id
    with encrypted_path.open("rb") as src:
        nonce = src.read(12)
        src.seek(0, os.SEEK_END)
        length = src.tell()
        if len(nonce) != 12 or length < 28:
            raise ValueError("Objeto criptografado truncado.")
        src.seek(length - 16)
        tag = src.read(16)
        src.seek(12)
        remaining = length - 28
        decryptor = Cipher(algorithms.AES(key), modes.GCM(nonce, tag)).decryptor()
        aad = ("AOC-MIGRATION-FILE-v1:" + object_id).encode()
        decryptor.authenticate_additional_data(aad)
        digest = hashlib.sha256()
        size = 0
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_name(output.name + ".aoc-partial")
        try:
            with temporary.open("wb") as dst:
                while remaining:
                    block = src.read(min(CHUNK, remaining))
                    if not block:
                        raise ValueError("Objeto criptografado incompleto.")
                    remaining -= len(block)
                    plain = decryptor.update(block)
                    if plain:
                        dst.write(plain)
                        digest.update(plain)
                        size += len(plain)
                tail = decryptor.finalize()
                if tail:
                    dst.write(tail)
                    digest.update(tail)
                    size += len(tail)
                dst.flush()
                os.fsync(dst.fileno())
            if size != record["size"] or digest.hexdigest() != record["sha256"]:
                raise ValueError("SHA-256 ou tamanho não corresponde após descriptografia.")
            os.replace(temporary, output)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise


def safe_restore_relative(raw: str) -> Path:
    if not isinstance(raw, str) or not raw or "\\\\" in raw:
        raise ValueError("Caminho de arquivo inválido no manifesto.")
    relative = PurePosixPath(raw)
    if relative.is_absolute() or any(part in ("", ".", "..") or ":" in part for part in relative.parts):
        raise ValueError("Caminho inseguro no manifesto.")
    return Path(*relative.parts)


def do_restore(vault_input: str, destination_input: str, password: str):
    vault = Path(vault_input).expanduser().resolve(strict=True)
    destination = Path(destination_input).expanduser().resolve(strict=False)
    if destination == vault or destination in vault.parents or vault in destination.parents:
        raise ValueError("A pasta de restauração não pode ser a pasta do cofre nem conter/estar dentro dela.")
    if destination.exists():
        raise ValueError("Escolha uma pasta de destino que ainda não exista. Nenhum arquivo será sobrescrito.")
    key, manifest = vault_open(vault, password)
    verification = do_verify(str(vault), password)
    if not verification["success"]:
        raise ValueError("O cofre não passou na verificação completa. Restauração bloqueada: " + verification["message"])
    roots = manifest.get("roots")
    records = manifest.get("files")
    if not isinstance(roots, list) or not isinstance(records, list):
        raise ValueError("Manifesto inválido.")
    staging = destination.with_name(destination.name + ".aoc-staging-" + secrets.token_hex(5))
    staging.mkdir(parents=True, exist_ok=False)
    restored = 0
    try:
        for record in records:
            root_index = record.get("root")
            if not isinstance(root_index, int) or root_index < 0 or root_index >= len(roots):
                raise ValueError("Origem inválida no manifesto.")
            relative = safe_restore_relative(record.get("path"))
            source_root = str(roots[root_index]).replace("\\\\", "/")
            root_label = f"{root_index + 1:02d}_" + safe_name(PurePosixPath(source_root).name or ("origem_" + str(root_index + 1)))
            output = (staging / root_label / relative).resolve(strict=False)
            if staging.resolve(strict=False) not in output.parents:
                raise ValueError("Caminho de restauração escapou da pasta de destino.")
            decrypt_stream_to_path(vault, record, key, output)
            restored += 1
        report = {"success": True, "files_restored": restored, "files_expected": len(records),
                  "errors": [], "destination": str(destination),
                  "message": "Todos os arquivos foram autenticados, verificados e restaurados."}
        (staging / "AOC_RESTORE_REPORT.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.replace(staging, destination)
        return report
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def do_verify(vault_input: str, password: str):
    vault = Path(vault_input).expanduser().resolve(strict=True)
    key, manifest = vault_open(vault, password)
    good, bad = 0, []
    for record in manifest["files"]:
        try:
            object_id = record["id"]
            if not isinstance(object_id, str) or not object_id.endswith(".bin") or not object_id[:-4].isdigit():
                raise ValueError("Identificador de objeto inválido.")
            verify_stream(vault / "objects" / object_id, key,
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

    def _check_host(self):
        if self.headers.get("Host") not in (f"127.0.0.1:{PORT}", f"localhost:{PORT}"):
            raise ValueError("Host local não permitido.")

    def do_GET(self):
        try:
            self._check_host()
        except ValueError:
            self.send_error(403)
            return
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
            self._check_host()
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
            elif self.path == "/api/restore":
                if not LOCK.acquire(blocking=False):
                    raise ValueError("Outra operação já está em andamento.")
                try:
                    result = do_restore(data["vault"], data["destination"], data["password"])
                finally:
                    LOCK.release()
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
