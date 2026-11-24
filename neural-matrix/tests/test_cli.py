import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from neural_matrix.cli import main
from neural_matrix.data import iter_jsonl


class CLITests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(self.folder.name)
        self.config = self.root / "config.json"
        self.config.write_text(json.dumps({
            "logical_units": 100,
            "logical_connections": 200,
            "active_units": 8,
            "active_edges": 16,
            "expert_count": 2,
            "expert_width": 2,
            "top_k_experts": 1,
            "learning_rate": 0.001,
            "seed": 17,
            "max_active_units": 16,
            "max_active_edges": 32,
            "memory_limit_mb": 4,
            "virtual_cache_mb": 1,
            "max_workers": 2
        }), encoding="utf-8")
        self.data = self.root / "data.jsonl"
        self.data.write_text(
            '{"x":[0.1,0.2],"y":[0.0,0.1]}\n'
            '{"x":[0.3,0.4],"y":[0.2,0.3]}\n',
            encoding="utf-8"
        )
        self.checkpoint = self.root / "model.json"

    def tearDown(self):
        self.folder.cleanup()

    def run_cli(self, args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(args)
        return code, output.getvalue()

    def test_generate_command_creates_dataset_compatible_with_training(self):
        generated = self.root / "generated.jsonl"
        code, output = self.run_cli([
            "generate", "--output", str(generated), "--samples", "3",
            "--width", "2", "--seed", "7"
        ])
        self.assertEqual(code, 0, output)
        self.assertEqual(json.loads(output)["samples"], 3)
        self.assertEqual(len(list(iter_jsonl(generated, 2, 2))), 3)

    def test_train_predict_resume_and_evaluate_work_end_to_end(self):
        base = ["--config", str(self.config)]
        code, output = self.run_cli(base + [
            "train", "--data", str(self.data), "--checkpoint", str(self.checkpoint),
            "--epochs", "2", "--batch-size", "1", "--mode", "incremental"
        ])
        self.assertEqual(code, 0, output)
        trained = json.loads(output)
        self.assertEqual(trained["samples"], 4)
        self.assertTrue(self.checkpoint.exists())

        code, output = self.run_cli([
            "predict", "--checkpoint", str(self.checkpoint), "--input", "[0.1,0.2]"
        ])
        self.assertEqual(code, 0, output)
        self.assertEqual(len(json.loads(output)["prediction"]), 2)

        code, output = self.run_cli([
            "evaluate", "--checkpoint", str(self.checkpoint), "--data", str(self.data)
        ])
        self.assertEqual(code, 0, output)
        self.assertEqual(json.loads(output)["samples"], 2)

        code, output = self.run_cli(base + [
            "train", "--data", str(self.data), "--checkpoint", str(self.checkpoint),
            "--epochs", "1", "--batch-size", "2", "--mode", "parallel"
        ])
        self.assertEqual(code, 0, output)
        self.assertEqual(json.loads(output)["samples"], 2)

    def test_predict_rejects_non_json_input_without_traceback(self):
        output = io.StringIO()
        error = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
            code = main(["predict", "--checkpoint", str(self.root / "missing.json"), "--input", "not-json"])
        self.assertNotEqual(code, 0)
        self.assertIn("error", error.getvalue().lower())


if __name__ == "__main__":
    unittest.main()
