#!/usr/bin/env python3
import argparse
import getpass
import hashlib
import json
import os
import platform
import re
import shutil
import stat
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

FORMAT_VERSION = 1
MANIFEST_NAME = "MIGRATION_MANIFEST.json"
CHUNK_SIZE = 4 * 1024 * 1024


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def safe_name(value):
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value).strip())
    return cleaned.strip("._") or "source"


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while True:
            chunk = stream.read(CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".manifest-", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def is_relative_to(path, parent):
    try:
        Path(path).resolve(strict=False).relative_to(Path(parent).resolve(strict=False))
        return True
    except ValueError:
        return False


def validate_source(source, destination):
    source = Path(source).expanduser().resolve(strict=True)
    destination = Path(destination).expanduser().resolve(strict=False)
    if not source.is_dir():
        raise ValueError("A origem precisa ser uma pasta: " + str(source))
    if source == Path(source.anchor):
        raise ValueError("Não copie uma unidade ou a raiz inteira. Escolha a pasta do usuário.")
    blocked = {
        "/etc", "/usr", "/var", "/proc", "/sys", "/dev", "/boot", "/run", "/bin", "/sbin", "/lib", "/lib64",
    }
    normalized = str(source).replace("\\", "/").rstrip("/").lower()
    if normalized in blocked:
        raise ValueError("A origem selecionada parece ser uma pasta do sistema: " + str(source))
    if os.name == "nt":
        system_root = Path(os.environ.get("SystemRoot", r"C:\Windows")).resolve(strict=False)
        program_files = [
            Path(os.environ.get("ProgramFiles", r"C:\Program Files")).resolve(strict=False),
            Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")).resolve(strict=False),
            Path(os.environ.get("ProgramData", r"C:\ProgramData")).resolve(strict=False),
        ]
        forbidden = [system_root, *program_files]
        if any(source == item or is_relative_to(source, item) for item in forbidden):
            raise ValueError("A origem selecionada é uma pasta do Windows, não um perfil de usuário.")
    if destination == source or is_relative_to(destination, source):
        raise ValueError("O destino do backup não pode ficar dentro da pasta de origem.")
    return source


def iter_regular_files(root, scan_errors=None):
    def record(error, fallback):
        if scan_errors is not None:
            scan_errors.append({
                "path": str(getattr(error, "filename", None) or fallback),
                "error": str(error),
            })

    def onerror(error):
        record(error, root)

    for current, directories, filenames in os.walk(root, topdown=True, followlinks=False, onerror=onerror):
        current_path = Path(current)
        kept = []
        for name in directories:
            item = current_path / name
            try:
                mode = item.lstat().st_mode
                if stat.S_ISDIR(mode) and not item.is_symlink():
                    kept.append(name)
            except OSError as error:
                record(error, item)
        directories[:] = kept
        for name in filenames:
            item = current_path / name
            try:
                mode = item.lstat().st_mode
                if stat.S_ISREG(mode):
                    yield item
            except OSError as error:
                record(error, item)


def load_manifest(backup_root):
    path = Path(backup_root) / MANIFEST_NAME
    if not path.is_file():
        raise FileNotFoundError("Manifesto não encontrado: " + str(path))
    with path.open("r", encoding="utf-8") as stream:
        manifest = json.load(stream)
    if manifest.get("format_version") != FORMAT_VERSION:
        raise ValueError("Versão de manifesto não suportada.")
    if not isinstance(manifest.get("files"), list) or not isinstance(manifest.get("roots"), list):
        raise ValueError("Manifesto inválido: campos obrigatórios ausentes.")
    return manifest


def safe_backup_path(backup_root, relative):
    relative_path = PurePosixPath(str(relative))
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValueError("Caminho inválido no manifesto: " + str(relative))
    candidate = Path(backup_root).joinpath(*relative_path.parts)
    if not is_relative_to(candidate, backup_root):
        raise ValueError("Caminho fora da pasta de backup: " + str(relative))
    return candidate


def new_manifest(label):
    return {
        "format_version": FORMAT_VERSION,
        "created_at": now_utc(),
        "updated_at": now_utc(),
        "computer": {
            "label": label,
            "hostname": platform.node(),
            "user": getpass.getuser(),
            "platform": platform.platform(),
            "architecture": platform.machine(),
            "python": platform.python_version(),
        },
        "roots": [],
        "files": [],
        "errors": [],
    }


def backup(args):
    destination = Path(args.destination).expanduser().resolve(strict=False)
    sources = [Path(item).expanduser() for item in args.source] if args.source else [Path.home()]
    checked_sources = [validate_source(item, destination) for item in sources]

    if args.dry_run:
        total_files = 0
        total_bytes = 0
        print("SIMULAÇÃO — nenhum arquivo será copiado.")
        scan_failures = 0
        for source in checked_sources:
            count = 0
            size = 0
            scan_errors = []
            for item in iter_regular_files(source, scan_errors):
                try:
                    size += item.stat().st_size
                    count += 1
                except OSError as error:
                    scan_errors.append({"path": str(item), "error": str(error)})
            scan_failures += len(scan_errors)
            total_files += count
            total_bytes += size
            print(str(source) + ": " + str(count) + " arquivos, " + str(size) + " bytes, " + str(len(scan_errors)) + " falhas de leitura")
        print("Total: " + str(total_files) + " arquivos, " + str(total_bytes) + " bytes")
        return 2 if scan_failures else 0

    manifest_path = destination / MANIFEST_NAME
    if destination.exists() and any(destination.iterdir()) and not manifest_path.exists():
        raise FileExistsError("O destino já contém dados e não possui manifesto. Escolha outra pasta.")
    destination.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(destination) if manifest_path.exists() else new_manifest(args.label)
    manifest["computer"]["label"] = args.label
    manifest["updated_at"] = now_utc()
    manifest["errors"] = []

    root_map = {item["key"]: item for item in manifest["roots"]}
    file_map = {(item["root_key"], item["relative_path"]): item for item in manifest["files"]}
    copied = 0
    unchanged = 0
    failed = 0
    processed = 0

    for index, source in enumerate(checked_sources, start=1):
        root_key = str(index).zfill(3) + "_" + safe_name(source.name or args.label)
        if root_key not in root_map:
            root_info = {"key": root_key, "source_path": str(source), "name": source.name or args.label}
            manifest["roots"].append(root_info)
            root_map[root_key] = root_info

        scan_errors = []
        for source_file in iter_regular_files(source, scan_errors):
            processed += 1
            relative = source_file.relative_to(source).as_posix()
            backup_relative = (PurePosixPath("files") / root_key / PurePosixPath(relative)).as_posix()
            target = safe_backup_path(destination, backup_relative)
            temporary = target.with_name(target.name + ".partial")
            try:
                source_stat = source_file.stat()
                source_hash = sha256_file(source_file)
                target.parent.mkdir(parents=True, exist_ok=True)
                already_good = target.is_file() and target.stat().st_size == source_stat.st_size and sha256_file(target) == source_hash
                if already_good:
                    unchanged += 1
                else:
                    if temporary.exists():
                        temporary.unlink()
                    shutil.copy2(source_file, temporary)
                    if sha256_file(temporary) != source_hash:
                        raise OSError("A verificação SHA-256 falhou após a cópia.")
                    os.replace(temporary, target)
                    copied += 1

                record = {
                    "root_key": root_key,
                    "relative_path": relative,
                    "backup_path": backup_relative,
                    "size": source_stat.st_size,
                    "sha256": source_hash,
                    "modified_time_ns": source_stat.st_mtime_ns,
                }
                file_map[(root_key, relative)] = record
            except Exception as error:
                failed += 1
                manifest["errors"].append({
                    "source_path": str(source_file),
                    "error": str(error),
                    "recorded_at": now_utc(),
                })
                try:
                    if temporary.exists():
                        temporary.unlink()
                except OSError:
                    pass

            if processed % 25 == 0:
                manifest["files"] = list(file_map.values())
                manifest["updated_at"] = now_utc()
                atomic_json(manifest_path, manifest)
                print("Processados: " + str(processed) + " | novos: " + str(copied) + " | já existentes: " + str(unchanged) + " | falhas: " + str(failed))

        for scan_error in scan_errors:
            failed += 1
            manifest["errors"].append({
                "source_path": scan_error["path"],
                "error": "Falha ao percorrer a pasta: " + scan_error["error"],
                "recorded_at": now_utc(),
            })

    manifest["files"] = sorted(file_map.values(), key=lambda item: (item["root_key"], item["relative_path"]))
    manifest["updated_at"] = now_utc()
    atomic_json(manifest_path, manifest)
    print("Backup concluído: " + str(destination))
    print("Arquivos processados: " + str(processed))
    print("Copiados/atualizados: " + str(copied))
    print("Já íntegros: " + str(unchanged))
    print("Falhas: " + str(failed))
    print("Manifesto: " + str(manifest_path))
    return 2 if failed else 0


def verify(args):
    backup_root = Path(args.backup).expanduser().resolve(strict=True)
    manifest = load_manifest(backup_root)
    good = 0
    bad = []
    for record in manifest["files"]:
        try:
            stored = safe_backup_path(backup_root, record["backup_path"])
            if not stored.is_file():
                raise FileNotFoundError("arquivo ausente")
            if stored.stat().st_size != record["size"]:
                raise ValueError("tamanho diferente")
            if sha256_file(stored) != record["sha256"]:
                raise ValueError("SHA-256 diferente")
            good += 1
        except Exception as error:
            bad.append((record.get("backup_path", "?"), str(error)))
    for recorded_error in manifest.get("errors", []):
        bad.append((recorded_error.get("source_path", "?"), "falha registrada durante o backup: " + recorded_error.get("error", "erro desconhecido")))
    print("Verificados: " + str(good) + "/" + str(len(manifest["files"])))
    for path, error in bad:
        print("FALHA: " + path + " — " + error)
    print("Resultado: " + ("ÍNTEGRO" if not bad else "INCOMPLETO OU ALTERADO"))
    return 0 if not bad else 2


def restore(args):
    backup_root = Path(args.backup).expanduser().resolve(strict=True)
    manifest = load_manifest(backup_root)
    target_root = Path(args.destination).expanduser().resolve(strict=False) if args.destination else Path.home() / "Desktop" / "ARQUIVOS_AOC"
    if target_root == backup_root or is_relative_to(target_root, backup_root):
        raise ValueError("A restauração não pode ser feita dentro da própria pasta de backup.")
    target_root.mkdir(parents=True, exist_ok=True)
    restored = 0
    unchanged = 0
    conflicts = 0
    failed = 0

    for record in manifest["files"]:
        try:
            stored = safe_backup_path(backup_root, record["backup_path"])
            if not stored.is_file() or sha256_file(stored) != record["sha256"]:
                raise ValueError("O arquivo do backup não passou na verificação.")
            output = target_root / record["root_key"] / Path(*PurePosixPath(record["relative_path"]).parts)
            if not is_relative_to(output, target_root):
                raise ValueError("Caminho de restauração inválido.")
            output.parent.mkdir(parents=True, exist_ok=True)
            if output.exists():
                same = output.is_file() and output.stat().st_size == record["size"] and sha256_file(output) == record["sha256"]
                if same:
                    unchanged += 1
                    continue
                if not args.overwrite:
                    conflicts += 1
                    print("CONFLITO (mantido): " + str(output))
                    continue
            temporary = output.with_name(output.name + ".restore-partial")
            if temporary.exists():
                temporary.unlink()
            shutil.copy2(stored, temporary)
            if sha256_file(temporary) != record["sha256"]:
                raise OSError("A verificação SHA-256 falhou na restauração.")
            os.replace(temporary, output)
            restored += 1
        except Exception as error:
            failed += 1
            print("FALHA: " + str(record.get("backup_path", "?")) + " — " + str(error))

    report = {
        "restored_at": now_utc(),
        "backup": str(backup_root),
        "destination": str(target_root),
        "restored": restored,
        "unchanged": unchanged,
        "conflicts": conflicts,
        "failed": failed,
        "backup_scan_or_copy_errors": len(manifest.get("errors", [])),
    }
    atomic_json(target_root / "RESTORE_REPORT.json", report)
    print("Restauração: " + str(target_root))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 2 if failed or manifest.get("errors") else 0


def system_info(_args):
    data = {
        "hostname": platform.node(),
        "user": getpass.getuser(),
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python": platform.python_version(),
        "home": str(Path.home()),
    }
    if sys.platform.startswith("linux"):
        meminfo = Path("/proc/meminfo")
        if meminfo.exists():
            for line in meminfo.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.startswith("MemTotal:"):
                    data["memory_kib"] = int(line.split()[1])
                    break
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


def build_parser():
    parser = argparse.ArgumentParser(prog="aoc-migrate", description="Backup verificável e restauração de arquivos de usuário.")
    commands = parser.add_subparsers(dest="command", required=True)

    backup_parser = commands.add_parser("backup", help="Copia o perfil do usuário para uma pasta de backup.")
    backup_parser.add_argument("--destination", required=True, help="Pasta em outro disco, HD externo ou rede.")
    backup_parser.add_argument("--source", action="append", help="Pasta adicional de origem; pode ser repetida. Sem ela, usa a pasta do usuário.")
    backup_parser.add_argument("--label", default="AOC", help="Nome da máquina no manifesto.")
    backup_parser.add_argument("--dry-run", action="store_true", help="Conta arquivos e bytes sem copiar.")
    backup_parser.set_defaults(handler=backup)

    verify_parser = commands.add_parser("verify", help="Verifica todos os arquivos com SHA-256.")
    verify_parser.add_argument("--backup", required=True, help="Pasta MIGRACAO_AOC.")
    verify_parser.set_defaults(handler=verify)

    restore_parser = commands.add_parser("restore", help="Restaura para a Área de Trabalho sem sobrescrever por padrão.")
    restore_parser.add_argument("--backup", required=True, help="Pasta MIGRACAO_AOC.")
    restore_parser.add_argument("--destination", help="Destino; padrão: Área de Trabalho/ARQUIVOS_AOC.")
    restore_parser.add_argument("--overwrite", action="store_true", help="Autoriza substituir arquivos diferentes no destino.")
    restore_parser.set_defaults(handler=restore)

    info_parser = commands.add_parser("info", help="Mostra informações básicas do computador.")
    info_parser.set_defaults(handler=system_info)
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.handler(args)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print("ERRO: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
