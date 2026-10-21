import pytest

from deta.verification import collect_project_files, verify_bundle


def passing_runner():
    return True


def test_verifier_has_four_independent_checks():
    report = verify_bundle({"app.py": "def hello():\n    return 42\n"}, test_runner=passing_runner)
    assert len(report.checks) == 4
    assert report.passed


def test_tests_are_not_assumed_to_have_run():
    report = verify_bundle({"app.py": "print('ok')\n"})
    assert len(report.checks) == 4
    assert not report.passed
    assert report.checks[2].name == "tests"
    assert not report.checks[2].passed


def test_dynamic_execution_is_flagged():
    report = verify_bundle({"app.py": "result = eval(user_input)\n"}, test_runner=passing_runner)
    assert not report.checks[1].passed


def test_syntax_error_is_flagged():
    report = verify_bundle({"app.py": "def broken(:\n    pass\n"}, test_runner=passing_runner)
    assert not report.checks[0].passed


def test_external_reference_needs_license_and_source():
    code = "\n".join([
        "def sample_function(value):",
        "    first = value + 7",
        "    second = first * 2",
        "    third = second - 4",
        "    fourth = third // 3",
        "    fifth = fourth + value",
        "    sixth = fifth * 8",
        "    return sixth",
    ])
    reference = {
        "content": code,
        "source_url": "https://github.com/example/repo/blob/main/example.py",
        "license_id": "MIT",
        "source_type": "code",
    }
    report = verify_bundle({"app.py": code}, references=[reference], test_runner=passing_runner)
    assert not report.checks[3].passed


def test_project_scanner_skips_generated_and_environment_directories(tmp_path):
    (tmp_path / "app.py").write_text("def hello():\n    return 42\n", encoding="utf-8")
    environment = tmp_path / ".venv" / "lib"
    environment.mkdir(parents=True)
    (environment / "bad.py").write_text("def broken(:\n    pass\n", encoding="utf-8")

    files = collect_project_files(tmp_path)

    assert list(files) == ["app.py"]


def test_project_scanner_enforces_file_count_and_byte_budgets(tmp_path):
    (tmp_path / "one.py").write_text("print(1)\n", encoding="utf-8")
    (tmp_path / "two.py").write_text("print(2)\n", encoding="utf-8")

    with pytest.raises(ValueError, match="file verification limit"):
        collect_project_files(tmp_path, max_files=1)

    with pytest.raises(ValueError, match="verification budget"):
        collect_project_files(tmp_path, max_bytes=4)


def test_project_scanner_rejects_empty_project(tmp_path):
    with pytest.raises(ValueError, match="No supported source files"):
        collect_project_files(tmp_path)


def test_project_scanner_rejects_non_directory(tmp_path):
    candidate = tmp_path / "source.py"
    candidate.write_text("print(1)\n", encoding="utf-8")
    with pytest.raises(ValueError, match="not a directory"):
        collect_project_files(candidate)

def test_static_analysis_does_not_flag_example_code_inside_a_string():
    report = verify_bundle(
        {"example.py": 'def test_example():\n    sample = "eval(user_input)"\n    return sample\n'},
        test_runner=passing_runner,
    )
    assert report.checks[0].passed
    assert report.checks[1].passed

