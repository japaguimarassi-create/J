import unittest
from socializer.core import build_system_prompt, validate_messages


class CoreTests(unittest.TestCase):
    def test_context_is_in_prompt(self):
        prompt = build_system_prompt("grupo falando de jogos", "entrar no papo", "enturmar", "casual")
        self.assertIn("grupo falando de jogos", prompt)
        self.assertIn("entrar no papo", prompt)
        self.assertIn("Tom solicitado", prompt)

    def test_unknown_mode_falls_back(self):
        prompt = build_system_prompt(mode="unknown", tone="unknown")
        self.assertIn("parceiro de papo atento", prompt)
        self.assertIn("Tom solicitado", prompt)

    def test_validate_dialogue(self):
        ok, message = validate_messages([
            {"role": "user", "content": "Oi"},
            {"role": "assistant", "content": "E aí!"},
        ])
        self.assertTrue(ok, message)

    def test_reject_invalid_role(self):
        ok, _ = validate_messages([
            {"role": "system", "content": "persona"},
            {"role": "human", "content": "Oi"},
            {"role": "assistant", "content": "Olá"},
        ])
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
