import tempfile
import unittest
from pathlib import Path

from ai.prepare_data import collect_documents, redact_secrets, source_files


class DataSafetyTests(unittest.TestCase):
    def test_common_credentials_are_redacted(self):
        github_token = "ghp_" + ("A" * 32)
        source = "API_KEY=very_secret_value_123\nAuthorization: Bearer abc.def.ghi\npassword: hunter2\ntoken = " + github_token + "\nconst safe = true\n"
        cleaned = redact_secrets(source)
        self.assertNotIn("very_secret_value_123", cleaned)
        self.assertNotIn("abc.def.ghi", cleaned)
        self.assertNotIn("hunter2", cleaned)
        self.assertNotIn(github_token, cleaned)
        self.assertIn("const safe = true", cleaned)

    def test_dependency_and_data_dirs_are_excluded_relative_to_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            (root / "src").mkdir(parents=True)
            (root / "data").mkdir()
            (root / "node_modules").mkdir()
            (root / "src" / "main.py").write_text("print('ok')", encoding="utf-8")
            (root / "data" / "old.py").write_text("private = True", encoding="utf-8")
            (root / "node_modules" / "module.py").write_text("dependency = True", encoding="utf-8")
            paths = {path.relative_to(root).as_posix() for path in source_files(root)}
            self.assertEqual(paths, {"src/main.py"})

    def test_secret_file_is_excluded_when_selected_directly(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("API_KEY=hidden", encoding="utf-8")
            self.assertEqual(list(source_files(path)), [])

    def test_exact_duplicates_do_not_cross_train_validation_split(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            root.mkdir()
            repeated = "def compute(value):\n    return value * value\n" * 30
            (root / "a.py").write_text(repeated, encoding="utf-8")
            (root / "b.py").write_text(repeated, encoding="utf-8")
            (root / "c.py").write_text("def add(a, b):\n    return a + b\n" * 80, encoding="utf-8")
            (root / "d.py").write_text("class Engine:\n    def run(self):\n        return 'ok'\n" * 80, encoding="utf-8")
            train, valid, skipped, _ = collect_documents(root, 100000, 1000000, 0.05)
            self.assertGreaterEqual(skipped, 1)
            self.assertTrue(train)
            self.assertTrue(valid)
            self.assertTrue({block for _, block in train}.isdisjoint({block for _, block in valid}))
            self.assertEqual(len({block for _, block in train + valid}), len(train) + len(valid))


if __name__ == "__main__":
    unittest.main()
