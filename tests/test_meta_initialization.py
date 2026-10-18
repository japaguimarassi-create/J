import unittest
import torch

from ai.config import tiny_config
from ai.model import KoworkLM


class MetaInitializationTests(unittest.TestCase):
    def test_meta_constructor_and_assign_loading(self):
        config = tiny_config(vocab_size=512)
        source = KoworkLM(config)
        source_state = {name: value.detach().clone() for name, value in source.state_dict().items()}
        target = KoworkLM(config, device="meta")
        self.assertTrue(all(parameter.device.type == "meta" for parameter in target.parameters()))
        incompatible = target.load_state_dict(source_state, assign=True)
        self.assertEqual(list(incompatible.missing_keys), [])
        self.assertEqual(list(incompatible.unexpected_keys), [])
        self.assertEqual(target.embed_tokens.weight.device.type, "cpu")
        self.assertTrue(torch.equal(target.embed_tokens.weight, source.embed_tokens.weight))


if __name__ == "__main__":
    unittest.main()
