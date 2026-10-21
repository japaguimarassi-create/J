import json
import os
import re
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


def validate_repo_name(full_name: str) -> tuple[str, str]:
    value = (full_name or "").strip()
    match = re.fullmatch(r"([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)", value)
    if not match or value in {".", ".."} or ".." in value:
        raise ValueError("Repository must use the OWNER/REPO form.")
    return match.group(1), match.group(2)


class GithubCatalog:
    def __init__(self, token: str | None = None, timeout: int = 20):
        self.token = token or os.getenv("DETA_GITHUB_TOKEN")
        self.timeout = timeout

    def _get_json(self, url: str) -> dict[str, Any]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "Deta-AI-Research/0.1",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code in {401, 403, 429}:
                raise GithubCatalogError(
                    f"GitHub API limit or permission error ({exc.code}); wait or configure DETA_GITHUB_TOKEN."
                ) from exc
            raise GithubCatalogError(f"GitHub API returned HTTP {exc.code}.") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise GithubCatalogError(f"GitHub API connection failed: {exc}") from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise GithubCatalogError("GitHub API returned invalid JSON.") from exc
        if not isinstance(payload, dict):
            raise GithubCatalogError("Unexpected GitHub API response.")
        return payload

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
        selected = []
        for entry in tree.get("tree", []):
            if not isinstance(entry, dict) or entry.get("type") != "blob":
                continue
            path = str(entry.get("path", ""))
            parts = [part.lower() for part in path.split("/")]
            if not path or any(part in BLOCKED_NAMES for part in parts):
                continue
            if any(part.startswith(".env") for part in parts):
                continue
            if path.lower().endswith((".min.js", ".map", ".lock")):
                continue
            if any(path.lower().endswith(ext) for ext in CODE_EXTENSIONS) and 0 < int(entry.get("size", 0)) <= 100_000:
                selected.append(path)
            if len(selected) >= max_files:
                break
        records = []
        for path in selected:
            encoded_path = urllib.parse.quote(path, safe="/")
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{encoded_branch}/{encoded_path}"
            request = urllib.request.Request(
                raw_url,
                headers={
                    "User-Agent": "Deta-AI-Research/0.1",
                    **({"Authorization": f"Bearer {self.token}"} if self.token else {}),
                },
            )
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    content = response.read(100_001)
                if len(content) > 100_000:
                    continue
                text = content.decode("utf-8")
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, UnicodeDecodeError):
                continue
            records.append({
                "content": text,
                "source_url": f"https://github.com/{owner}/{repo}/blob/{encoded_branch}/{encoded_path}",
                "license_id": license_id,
                "source_type": "code",
                "source_name": f"{owner}/{repo}",
                "path": path,
            })
        return records
