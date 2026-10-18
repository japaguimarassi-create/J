import unittest

import torch
from torch.nn import functional as F

from ai.config import estimate_parameters, tiny_config
from ai.model import KoworkLM


class ModelTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(7)
        self.config = tiny_config(vocab_size=512)
        self.model = KoworkLM(self.config)

    def test_parameter_count_matches_tensors(self):
        actual = sum(parameter.numel() for parameter in self.model.parameters())
        self.assertEqual(actual, estimate_parameters(self.config))

    def test_forward_and_backward(self):
        tokens = torch.randint(0, self.config.vocab_size, (2, 16))
        logits = self.model(tokens)
        self.assertEqual(tuple(logits.shape), (2, 16, self.config.vocab_size))
        loss = F.cross_entropy(logits.reshape(-1, self.config.vocab_size), tokens.reshape(-1))
        self.assertTrue(torch.isfinite(loss).item())
        loss.backward()
        self.assertIsNotNone(self.model.embed_tokens.weight.grad)

    def test_generation_length(self):
        prompt = torch.tensor([[10, 20, 30]], dtype=torch.long)
        result = self.model.generate(prompt, max_new_tokens=3, temperature=1.0, top_k=10)
        self.assertEqual(tuple(result.shape), (1, 6))

    def test_rejects_oversized_context(self):
        tokens = torch.randint(0, self.config.vocab_size, (1, self.config.max_seq_len + 1))
        with self.assertRaises(ValueError):
            self.model(tokens)


if __name__ == "__main__":
    unittest.main()
