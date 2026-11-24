import json
import tempfile
import unittest
from pathlib import Path

from neural_matrix.data import iter_batches, iter_jsonl


class DatasetTests(unittest.TestCase):
    def write_data(self, text):
        folder = tempfile.TemporaryDirectory()
        path = Path(folder.name) / "samples.jsonl"
        path.write_text(text, encoding="utf-8")
        self.addCleanup(folder.cleanup)
        return path

    def test_jsonl_reader_returns_numeric_vectors(self):
        path = self.write_data('{"x":[1,2],"y":[3,4]}\n')
        self.assertEqual(list(iter_jsonl(path, 2, 2)), [([1.0, 2.0], [3.0, 4.0])])

    def test_jsonl_reader_reports_malformed_line_number(self):
        path = self.write_data('{"x":[1,2],"y":[3,4]}\nnot-json\n')
        with self.assertRaisesRegex(ValueError, "line 2"):
            list(iter_jsonl(path, 2, 2))

    def test_jsonl_reader_rejects_non_finite_and_boolean_values(self):
        for value in ("NaN", "Infinity", "true"):
            with self.subTest(value=value):
                path = self.write_data('{"x":[%s,2],"y":[3,4]}\n' % value)
                with self.assertRaises(ValueError):
                    list(iter_jsonl(path, 2, 2))

    def test_jsonl_reader_rejects_width_mismatch(self):
        path = self.write_data('{"x":[1],"y":[3,4]}\n')
        with self.assertRaisesRegex(ValueError, "width"):
            list(iter_jsonl(path, 2, 2))

    def test_jsonl_reader_enforces_positive_limit(self):
        path = self.write_data('{"x":[1,2],"y":[3,4]}\n')
        with self.assertRaises(ValueError):
            list(iter_jsonl(path, 2, 2, limit=0))

    def test_jsonl_limit_stops_after_requested_samples(self):
        path = self.write_data(
            '{"x":[1,2],"y":[3,4]}\n{"x":[5,6],"y":[7,8]}\n'
        )
        self.assertEqual(len(list(iter_jsonl(path, 2, 2, limit=1))), 1)

    def test_empty_jsonl_yields_no_samples(self):
        path = self.write_data("")
        self.assertEqual(list(iter_jsonl(path, 2, 2)), [])

    def test_batches_never_exceed_configured_size(self):
        batches = list(iter_batches(iter(range(7)), 3))
        self.assertEqual(batches, [[0, 1, 2], [3, 4, 5], [6]])

    def test_batch_size_must_be_positive(self):
        with self.assertRaises(ValueError):
            list(iter_batches([1, 2], 0))


if __name__ == "__main__":
    unittest.main()
