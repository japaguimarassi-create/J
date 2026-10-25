import sys
import unittest
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ai"))
from model import ForgeStudent, MAX_SEQ_LEN, decode, encode
from train import make_stream, read_examples, sample_batch


class ModelTests(unittest.TestCase):
    def test_parameter_count_is_about_250k(self):
        model = ForgeStudent()
        count = sum(p.numel() for p in model.parameters())
        self.assertEqual(count, 247890)
        self.assertGreater(count, 240000)
        self.assertLess(count, 255000)

    def test_forward_has_expected_shape_and_finite_values(self):
        model = ForgeStudent()
        logits = model(torch.randint(0, 258, (2, 32)))
        self.assertEqual(tuple(logits.shape), (2, 32, 258))
        self.assertTrue(torch.isfinite(logits).all().item())

    def test_context_truncation(self):
        model = ForgeStudent()
        logits = model(torch.randint(0, 258, (1, MAX_SEQ_LEN + 12)))
        self.assertEqual(tuple(logits.shape), (1, MAX_SEQ_LEN, 258))

    def test_utf8_round_trip(self):
        phrase = "Animação 3D — FORGE"
        self.assertEqual(decode(encode(phrase, add_bos=False)), phrase)

    def test_training_stream(self):
        rows = read_examples(ROOT / "data" / "seed_examples.jsonl")
        self.assertGreaterEqual(len(rows), 30)
        stream = make_stream(rows)
        self.assertGreater(len(stream), MAX_SEQ_LEN + 2)
        x, y = sample_batch(stream, 2, "cpu")
        self.assertEqual(tuple(x.shape), (2, MAX_SEQ_LEN))
        self.assertEqual(tuple(y.shape), (2, MAX_SEQ_LEN))


if __name__ == "__main__":
    unittest.main()
