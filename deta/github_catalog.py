import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from deta.data import ALLOWED_CODE_LICENSES


class GithubCatalogError(RuntimeError):
    pass


CODE_EXTENSIONS = {
    ".c", ".cc", ".cpp", ".cs", ".gd", ".go", ".h", ".hpp", ".java",
    ".js", ".jsx", ".kt", ".kts", ".lua", ".php", ".py", ".rb", ".rs",
    ".scala", ".sh", ".swift", ".ts", ".tsx", ".vue",
}
BLOCKED_NAMES = {
    ".env", ".npmrc", ".pypirc", "credentials", "id_rsa", "id_ed25519",
    "secrets", "secret", "token", "private_key",
}
BLOCKED_DIRS = {".git", "node_modules", "vendor", "dist", "build", "target", "out"}
SPDX_PATTERN = re.compile(r"(?im)^\s*(?:#|//|/\*|\*|<!--)?\s*SPDX-License-Identifier:\s*([^\r\n*<>]+)")
SENSITIVE_CONTENT_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA |PGP )?PRIVATE KEY-----", re.IGNORECASE),
    re.compile(r"\b(?:gh[pousr]_[a-z0-9]{20,}|github_pat_[a-z0-9_]{20,}|AKIA[0-9A-Z]{16})\b"),
    re.compile(
        r"""(?i)\b(?:api[_-]?key|access[_-]?token|client[_-]?secret|password|passwd)\b\s*[:=]\s*["'][A-Za-z0-9/+=_-]{16,}["']"""
    ),
)


def validate_repo_name(full_name: str) -> tuple[str, str]:
    value = (full_name or "").strip()
    match = re.fullmatch(r"([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)", value)
    if not match or value in {".", ".."} or ".." in value:
        raise ValueError("Repository must use the OWNER/REPO form.")
    return match.group(1), match.group(2)


def _content_license(source_text: str, repository_license: str) -> str | None:
    match = SPDX_PATTERN.search(source_text[:4000])
    if not match:
        return repository_license
    declared = match.group(1).strip().rstrip("*/").strip()
    if re.search(r"\b(?:AND|OR|WITH)\b", declared, re.IGNORECASE):
        return None
    return declared


def _looks_sensitive(source_text: str) -> bool:
    return any(pattern.search(source_text) for pattern in SENSITIVE_CONTENT_PATTERNS)


class GithubCatalog:
    def __init__(self, token: str | None = None, timeout: int = 20, max_retries: int = 3):
        if timeout < 1 or timeout > 120:
            raise ValueError("timeout must be between 1 and 120 seconds")
        if not 0 <= max_retries <= 5:
            raise ValueError("max_retries must be between 0 and 5")
        self.token = token or os.getenv("DETA_GITHUB_TOKEN")
        self.timeout = timeout
        self.max_retries = max_retries
        self.max_retry_wait_seconds = 120

    def _get_json(self, url: str) -> dict[str, Any]:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https" or parsed.hostname != "api.github.com":
            raise ValueError("Authenticated GitHub API requests must target https://api.github.com.")
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "Deta-AI-Research/0.2",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(url, headers=headers)
        attempt = 0
        while True:
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                if not isinstance(payload, dict):
                    raise GithubCatalogError("Unexpected GitHub API response.")
                return payload
            except urllib.error.HTTPError as exc:
                try:
                    error_body = exc.read(2048).decode("utf-8", "replace").lower()
                except (AttributeError, OSError):
                    error_body = ""
                error_headers = exc.headers or {}
                retry_after = error_headers.get("Retry-After")
                remaining = error_headers.get("X-RateLimit-Remaining")
                rate_limited = (
                    exc.code == 429
                    or bool(retry_after)
                    or remaining == "0"
                    or "rate limit" in error_body
                )
                if not rate_limited or attempt >= self.max_retries:
                    raise GithubCatalogError(
                        f"GitHub API returned HTTP {exc.code}: {error_body[:180].strip()}"
                    ) from exc
                try:
                    delay = float(retry_after) if retry_after else None
                except (TypeError, ValueError):
                    delay = None
                if delay is None and remaining == "0":
                    try:
                        reset_at = float(error_headers.get("X-RateLimit-Reset", "0"))
                        delay = max(1.0, reset_at - time.time())
                    except (TypeError, ValueError):
                        delay = None
                if delay is None:
                    delay = min(60.0, 2.0 ** (attempt + 1))
                if delay > self.max_retry_wait_seconds:
                    raise GithubCatalogError(
                        f"GitHub rate limit requires waiting {delay:.0f}s; stop now and retry later."
                    ) from exc
                time.sleep(max(1.0, delay))
                attempt += 1
            except (urllib.error.URLError, TimeoutError) as exc:
                if attempt >= self.max_retries:
                    raise GithubCatalogError(f"GitHub API connection failed after retries: {exc}") from exc
                time.sleep(min(8.0, 2.0 ** attempt))
                attempt += 1
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise GithubCatalogError("GitHub API returned invalid JSON.") from exc

    def search_repositories(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        query = (query or "").strip()
        if not query:
            raise ValueError("Search query cannot be empty.")
        if not 1 <= limit <= 20:
            raise ValueError("limit must be between 1 and 20.")
        url = "https://api.github.com/search/repositories?" + urllib.parse.urlencode(
            {"q": query, "sort": "stars", "order": "desc", "per_page": limit}
        )
        payload = self._get_json(url)
        items = payload.get("items", [])
        if not isinstance(items, list):
            raise GithubCatalogError("GitHub search returned an invalid items collection.")
        return [
            {
                "full_name": item.get("full_name", ""),
                "html_url": item.get("html_url", ""),
                "description": item.get("description") or "",
                "license_id": (item.get("license") or {}).get("spdx_id", ""),
                "default_branch": item.get("default_branch", "main"),
            }
            for item in items
            if isinstance(item, dict)
        ]

    def fetch_licensed_code(self, full_name: str, max_files: int = 10) -> list[dict[str, Any]]:
        owner, repo = validate_repo_name(full_name)
        if not 1 <= max_files <= 25:
            raise ValueError("max_files must be between 1 and 25.")
        base = f"https://api.github.com/repos/{owner}/{repo}"
        metadata = self._get_json(base)
        is_public = metadata.get("private") is False or metadata.get("visibility") == "public"
        if metadata.get("private") is True or not is_public:
            raise GithubCatalogError("Only repositories explicitly marked public are eligible for ingestion.")
        license_id = ((metadata.get("license") or {}).get("spdx_id") or "").strip()
        if license_id not in ALLOWED_CODE_LICENSES:
            raise GithubCatalogError(
                f"Repository license '{license_id or 'unknown'}' is not on Deta's approved code-license list."
            )
        branch = metadata.get("default_branch") or "main"
        encoded_branch = urllib.parse.quote(branch, safe="")
        tree = self._get_json(f"{base}/git/trees/{encoded_branch}?recursive=1")
        if tree.get("truncated"):
            raise GithubCatalogError("Repository tree is truncated; ingest smaller repositories selectively.")
        entries = tree.get("tree", [])
        if not isinstance(entries, list):
            raise GithubCatalogError("GitHub repository tree is invalid.")
        selected = []
        for entry in entries:
            if not isinstance(entry, dict) or entry.get("type") != "blob":
                continue
            path = str(entry.get("path", ""))
            parts = [part.lower() for part in path.split("/")]
            if not path or any(part in BLOCKED_NAMES for part in parts):
                continue
            if any(part.startswith(".env") for part in parts):
                continue
            if any(part in BLOCKED_DIRS for part in parts[:-1]):
                continue
            if path.lower().endswith((".min.js", ".map", ".lock")):
                continue
            try:
                size = int(entry.get("size", 0))
            except (TypeError, ValueError):
                continue
            if any(path.lower().endswith(ext) for ext in CODE_EXTENSIONS) and 0 < size <= 100_000:
                selected.append(path)
            if len(selected) >= max_files:
                break

        records = []
        for path in selected:
            encoded_path = urllib.parse.quote(path, safe="/")
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{encoded_branch}/{encoded_path}"
            parsed_raw = urllib.parse.urlparse(raw_url)
            if parsed_raw.scheme != "https" or parsed_raw.hostname != "raw.githubusercontent.com":
                continue
            request = urllib.request.Request(
                raw_url,
                headers={"User-Agent": "Deta-AI-Research/0.2"},
            )
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    content = response.read(100_001)
                if len(content) > 100_000:
                    continue
                source_text = content.decode("utf-8")
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, UnicodeDecodeError):
                continue
            if _looks_sensitive(source_text):
                continue
            file_license = _content_license(source_text, license_id)
            if file_license not in ALLOWED_CODE_LICENSES:
                continue
            records.append({
                "content": source_text,
                "source_url": f"https://github.com/{owner}/{repo}/blob/{encoded_branch}/{encoded_path}",
                "license_id": file_license,
                "source_type": "code",
                "source_name": f"{owner}/{repo}",
                "path": path,
            })
        return records
