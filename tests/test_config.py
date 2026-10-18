import unittest

from ai.config import ModelConfig, estimate_parameters


class ConfigTests(unittest.TestCase):
    def test_10b_count(self):
        config = ModelConfig()
        self.assertEqual(estimate_parameters(config), 10046763008)

    def test_invalid_attention_shape_is_rejected(self):
        config = ModelConfig(hidden_size=128, num_attention_heads=6, num_key_value_heads=2)
        with self.assertRaises(ValueError):
            config.validate()


if __name__ == "__main__":
    unittest.main()
