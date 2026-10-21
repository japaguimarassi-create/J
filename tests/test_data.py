import json

from deta.data import allowed_license, read_licensed_jsonl, normalize_record


def test_code_and_text_licenses_are_separate():
    assert allowed_license("MIT", "code")
    assert not allowed_license("ODC-BY-1.0", "code")
    assert allowed_license("ODC-BY-1.0", "text")
    assert not allowed_license("NOASSERTION", "text")


def test_record_requires_provenance_and_allowed_license():
    good = normalize_record({
        "content": "print('hello')",
        "source_url": "https://github.com/example/repo/blob/main/app.py",
        "license_id": "MIT",
        "source_type": "code",
    })
    bad = normalize_record({
        "content": "print('hello')",
        "source_url": "https://github.com/example/repo/blob/main/app.py",
        "license_id": "NOASSERTION",
        "source_type": "code",
    })
    assert good is not None
    assert len(good["content_sha256"]) == 64
    assert bad is None


def test_jsonl_loader_filters_unlicensed_records(tmp_path):
    path = tmp_path / "data.jsonl"
    records = [
        {
            "content": "def useful_function():\n    return 42",
            "source_url": "https://github.com/example/repo/blob/main/app.py",
            "license_id": "MIT",
            "source_type": "code",
        },
        {
            "content": "not accepted",
            "source_url": "https://github.com/example/repo/blob/main/bad.py",
            "license_id": "NOASSERTION",
            "source_type": "code",
        },
    ]
    path.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")
    accepted = list(read_licensed_jsonl(path))
    assert len(accepted) == 1
    assert accepted[0]["license_id"] == "MIT"
