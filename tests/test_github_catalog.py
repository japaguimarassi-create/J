import pytest

from deta.github_catalog import GithubCatalog, validate_repo_name


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
