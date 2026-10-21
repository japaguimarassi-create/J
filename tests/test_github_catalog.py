import io
import urllib.error

import pytest

from deta.github_catalog import (
    GithubCatalog,
    _content_license,
    _looks_sensitive,
    validate_repo_name,
)


def test_valid_github_repository_name():
    assert validate_repo_name("owner/repo") == ("owner", "repo")
    assert validate_repo_name("owner-name/repo_name") == ("owner-name", "repo_name")


@pytest.mark.parametrize("value", ["", "../repo", "owner", "owner/repo/path", "https://github.com/a/b", "owner/.."])
def test_invalid_repository_names_are_rejected(value):
    with pytest.raises(ValueError):
        validate_repo_name(value)


def test_authenticated_api_helper_rejects_other_hosts():
    catalog = GithubCatalog(token="not-a-real-token")
    with pytest.raises(ValueError, match="api.github.com"):
        catalog._get_json("https://example.com/repos/owner/repo")


def test_download_never_sends_github_token_to_raw_host(monkeypatch):
    catalog = GithubCatalog(token="sensitive-token")

    def fake_get_json(url):
        if url == "https://api.github.com/repos/owner/repo":
            return {"license": {"spdx_id": "MIT"}, "default_branch": "main"}
        return {
            "truncated": False,
            "tree": [{"path": "example.py", "type": "blob", "size": 24}],
        }

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def read(self, amount=-1):
            content = b"def example():\n    return 42\n"
            return content if amount < 0 else content[:amount]

    captured = []

    def fake_urlopen(request, timeout):
        captured.append(request)
        return FakeResponse()

    monkeypatch.setattr(catalog, "_get_json", fake_get_json)
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    records = catalog.fetch_licensed_code("owner/repo", max_files=1)

    assert len(records) == 1
    assert captured
    assert captured[0].full_url.startswith("https://raw.githubusercontent.com/")
    assert captured[0].get_header("Authorization") is None
    assert records[0]["license_id"] == "MIT"


def test_sensitive_source_contents_are_excluded():
    assert _looks_sensitive('TOKEN = "ghp_0123456789abcdefghijklmnopqr"')
    assert _looks_sensitive('password = "12345678901234567890"')
    assert _looks_sensitive("-----BEGIN RSA PRIVATE KEY-----")
    assert not _looks_sensitive("def add(left, right):\n    return left + right\n")


def test_file_level_spdx_license_is_respected():
    assert _content_license("# SPDX-License-Identifier: MIT\nprint('x')", "Apache-2.0") == "MIT"
    assert _content_license("// SPDX-License-Identifier: GPL-3.0-only\ncode()", "MIT") == "GPL-3.0-only"
    assert _content_license("# SPDX-License-Identifier: MIT OR Apache-2.0\ncode()", "MIT") is None


def test_rate_limit_retry_waits_before_retrying(monkeypatch):
    catalog = GithubCatalog(max_retries=1)
    calls = []
    waits = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def read(self):
            return b'{"items": []}'

    def fake_urlopen(request, timeout):
        calls.append(request)
        if len(calls) == 1:
            raise urllib.error.HTTPError(
                request.full_url,
                429,
                "Too Many Requests",
                {"Retry-After": "1"},
                io.BytesIO(b"rate limit exceeded"),
            )
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr("time.sleep", waits.append)
    payload = catalog._get_json("https://api.github.com/repos/owner/repo")

    assert payload == {"items": []}
    assert len(calls) == 2
    assert waits == [1.0]
