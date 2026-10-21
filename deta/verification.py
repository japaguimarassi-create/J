import ast
import json
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from deta.data import ALLOWED_CODE_LICENSES, valid_source_url


@dataclass(frozen=True)
class VerificationCheck:
    name: str
    passed: bool
    details: str


@dataclass(frozen=True)
class VerificationReport:
    checks: tuple[VerificationCheck, ...]

    @property
    def passed(self) -> bool:
        return len(self.checks) == 4 and all(check.passed for check in self.checks)


PROJECT_SOURCE_SUFFIXES = {
    ".c", ".cc", ".cpp", ".cs", ".css", ".gd", ".go", ".gradle", ".h",
    ".hpp", ".html", ".java", ".js", ".jsx", ".json", ".kt", ".kts",
    ".lua", ".php", ".py", ".rb", ".rs", ".scala", ".sh", ".swift",
    ".toml", ".ts", ".tsx", ".vue", ".yaml", ".yml",
}
IGNORED_DIRS = {
    ".git", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".venv",
    "build", "dist", "node_modules", "out", "target", "venv",
}
DEFAULT_MAX_PROJECT_FILES = 500
DEFAULT_MAX_PROJECT_BYTES = 4 * 1024 * 1024


RISK_PATTERNS = {
    "dynamic execution": re.compile(r"\b(?:eval|exec)\s*\("),
    "shell command execution": re.compile(r"\bshell\s*=\s*True\b"),
    "embedded credential": re.compile(
        r"""(?i)\b(?:api[_-]?key|access[_-]?token|client[_-]?secret|password|passwd)\b\s*[:=]\s*["'][A-Za-z0-9/+=_-]{16,}["']"""
    ),
}
CREDENTIAL_NAMES = re.compile(r"(?:api[_-]?key|access[_-]?token|client[_-]?secret|password|passwd|secret|token)", re.I)
PLACEHOLDER_VALUES = {"changeme", "example", "placeholder", "redacted", "replace_me", "your_api_key"}


def collect_project_files(
    project_root: str | Path,
    max_files: int = DEFAULT_MAX_PROJECT_FILES,
    max_bytes: int = DEFAULT_MAX_PROJECT_BYTES,
) -> dict[str, str]:
    root = Path(project_root).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"Project path is not a directory: {root}")
    if not 1 <= max_files <= 5000:
        raise ValueError("max_files must be between 1 and 5000")
    if not 1 <= max_bytes <= 64 * 1024 * 1024:
        raise ValueError("max_bytes must be between 1 and 67108864")

    files: dict[str, str] = {}
    total_bytes = 0
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if path.is_symlink() or any(part.lower() in IGNORED_DIRS for part in relative.parts):
            continue
        if not path.is_file() or path.suffix.lower() not in PROJECT_SOURCE_SUFFIXES:
            continue
        if len(files) >= max_files:
            raise ValueError(
                f"Project exceeds the {max_files}-file verification limit; narrow the project root."
            )
        try:
            size = path.stat().st_size
        except OSError as exc:
            raise ValueError(f"Could not inspect {relative.as_posix()}: {exc}") from exc
        if size > max_bytes or total_bytes + size > max_bytes:
            raise ValueError(
                f"Project source exceeds the {max_bytes}-byte verification budget at {relative.as_posix()}."
            )
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise ValueError(f"Could not read UTF-8 source file {relative.as_posix()}: {exc}") from exc
        files[relative.as_posix()] = content
        total_bytes += size

    if not files:
        raise ValueError(f"No supported source files were found under {root}.")
    return files


def _python_and_json_syntax(files: Mapping[str, str]) -> list[str]:
    errors = []
    for path, content in files.items():
        try:
            suffix = Path(path).suffix.lower()
            if suffix == ".py":
                ast.parse(content, filename=path)
            elif suffix == ".json":
                json.loads(content)
            elif suffix == ".toml":
                tomllib.loads(content)
        except (SyntaxError, ValueError) as exc:
            errors.append(f"{path}: {exc}")
    return errors


def _assigned_names(target: ast.AST) -> set[str]:
    names = set()
    for node in ast.walk(target):
        if isinstance(node, ast.Name):
            names.add(node.id.lower())
        elif isinstance(node, ast.Attribute):
            names.add(node.attr.lower())
    return names


def _python_static_issues(path: str, content: str) -> list[str]:
    issues = []
    try:
        tree = ast.parse(content, filename=path)
    except SyntaxError:
        return ["syntax error prevents reliable Python static analysis"]

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in {"eval", "exec"}:
                issues.append(f"{path}: dynamic execution at line {node.lineno}")
            if any(
                keyword.arg == "shell"
                and isinstance(keyword.value, ast.Constant)
                and keyword.value.value is True
                for keyword in node.keywords
            ):
                issues.append(f"{path}: shell command execution at line {node.lineno}")
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            value = node.value
            if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
                continue
            literal = value.value.strip()
            if len(literal) >= 16 and literal.lower() not in PLACEHOLDER_VALUES:
                if any(CREDENTIAL_NAMES.search(name) for target in targets for name in _assigned_names(target)):
                    issues.append(f"{path}: possible embedded credential at line {node.lineno}")
    return issues


def _static_issues(files: Mapping[str, str]) -> list[str]:
    issues = []
    for path, content in files.items():
        if Path(path).suffix.lower() == ".py":
            issues.extend(_python_static_issues(path, content))
            continue
        for label, pattern in RISK_PATTERNS.items():
            if pattern.search(content):
                issues.append(f"{path}: {label}")
    return issues


def _tokens(content: str) -> list[str]:
    return re.findall(r"[A-Za-z_][A-Za-z_0-9]*|\d+|[^\s]", content.lower())


def _shingles(tokens: list[str], size: int = 5) -> set[tuple[str, ...]]:
    if len(tokens) < size:
        return {tuple(tokens)} if tokens else set()
    return {tuple(tokens[index:index + size]) for index in range(len(tokens) - size + 1)}


def _similarity(left: str, right: str) -> float:
    left_shingles = _shingles(_tokens(left))
    right_shingles = _shingles(_tokens(right))
    if not left_shingles or not right_shingles:
        return 0.0
    return len(left_shingles & right_shingles) / len(left_shingles | right_shingles)


def verify_bundle(
    files: Mapping[str, str],
    references: Iterable[Mapping[str, Any]] = (),
    test_runner: Callable[[], bool] | None = None,
    similarity_threshold: float = 0.88,
) -> VerificationReport:
    if not 0 < similarity_threshold <= 1:
        raise ValueError("similarity_threshold must be between 0 and 1")

    syntax_errors = _python_and_json_syntax(files)
    syntax_check = VerificationCheck(
        "syntax",
        not syntax_errors,
        "No supported syntax/format issues found." if not syntax_errors else "; ".join(syntax_errors),
    )

    static_issues = _static_issues(files)
    security_check = VerificationCheck(
        "static_security",
        not static_issues,
        "No configured high-risk patterns found." if not static_issues else "; ".join(static_issues),
    )

    if test_runner is None:
        tests_check = VerificationCheck(
            "tests",
            False,
            "Not run: configure a test runner isolated from secrets and production permissions.",
        )
    else:
        try:
            tests_passed = bool(test_runner())
            tests_check = VerificationCheck(
                "tests",
                tests_passed,
                "Configured test runner passed." if tests_passed else "Configured test runner failed.",
            )
        except Exception as exc:
            tests_check = VerificationCheck("tests", False, f"Test runner raised {type(exc).__name__}: {exc}")

    reference_issues = []
    for index, reference in enumerate(list(references)):
        url = str(reference.get("source_url", ""))
        license_id = str(reference.get("license_id", ""))
        source_type = str(reference.get("source_type", "code")).lower()
        if not valid_source_url(url):
            reference_issues.append(f"reference {index}: invalid or missing HTTPS source URL")
        if source_type != "code":
            reference_issues.append(f"reference {index}: expected code, found '{source_type}'")
        if license_id not in ALLOWED_CODE_LICENSES:
            reference_issues.append(f"reference {index}: license '{license_id or 'unknown'}' is not approved")
        sample = reference.get("content")
        if isinstance(sample, str) and sample.strip():
            for path, candidate in files.items():
                if len(_tokens(candidate)) < 20:
                    continue
                score = _similarity(candidate, sample)
                if score >= similarity_threshold:
                    reference_issues.append(f"{path}: similarity {score:.3f} with reference {index}")
    provenance_check = VerificationCheck(
        "provenance_similarity",
        not reference_issues,
        "References checked; no policy issue found." if not reference_issues else "; ".join(reference_issues),
    )
    return VerificationReport((syntax_check, security_check, tests_check, provenance_check))


def run_pytest_in_current_project(project_root: str | Path) -> bool:
    root = Path(project_root).resolve()
    if not (root / "tests").is_dir():
        return False
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=120,
        check=False,
        shell=False,
        env={"PATH": str(Path(sys.executable).parent), "PYTHONPATH": str(root)},
        text=True,
    )
    return result.returncode == 0
