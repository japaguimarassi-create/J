from deta.verification import verify_bundle


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
    }
    report = verify_bundle({"app.py": code}, references=[reference], test_runner=passing_runner)
    assert not report.checks[3].passed
