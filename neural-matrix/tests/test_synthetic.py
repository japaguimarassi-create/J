import json
import tempfile
import unittest
from pathlib import Path

from neural_matrix.data import iter_jsonl
from neural_matrix.synthetic import iter_synthetic, write_synthetic_jsonl


class SyntheticDataTests(unittest.TestCase):
    def test_generator_is_deterministic_for_same_seed(self):
        first = list(iter_synthetic(samples=4, width=3, seed=11))
        second = list(iter_synthetic(samples=4, width=3, seed=11))
        self.assertEqual(first, second)

    def test_generator_respects_sample_count_and_vector_width(self):
        samples = list(iter_synthetic(samples=5, width=4, seed=2))
        self.assertEqual(len(samples), 5)
        self.assertTrue(all(len(inputs) == 4 and len(target) == 4 for inputs, target in samples))

    def test_writer_creates_valid_jsonl_for_training(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "generated.jsonl"
            count = write_synthetic_jsonl(path, samples=7, width=3, seed=9)
            self.assertEqual(count, 7)
            self.assertEqual(len(list(iter_jsonl(path, 3, 3))), 7)

    def test_generator_rejects_non_positive_dimensions(self):
        for samples, width in ((0, 3), (3, 0), (-1, 2)):
            with self.subTest(samples=samples, width=width):
                with self.assertRaises(ValueError):
                    list(iter_synthetic(samples=samples, width=width))

    def test_writer_does_not_silently_overwrite_invalid_path(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "missing" / "generated.jsonl"
            with self.assertRaises(FileNotFoundError):
                write_synthetic_jsonl(path, samples=2, width=2, create_parent=False)


if __name__ == "__main__":
    unittest.main()
