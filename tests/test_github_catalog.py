import pytest

from deta.github_catalog import validate_repo_name


def test_valid_github_repository_name():
    assert validate_repo_name("owner/repo") == ("owner", "repo")
    assert validate_repo_name("owner-name/repo_name") == ("owner-name", "repo_name")


@pytest.mark.parametrize("value", ["", "../repo", "owner", "owner/repo/path", "https://github.com/a/b", "owner/.."])
def test_invalid_repository_names_are_rejected(value):
    with pytest.raises(ValueError):
        validate_repo_name(value)
