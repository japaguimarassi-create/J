import unittest

import server


class ServerAuthTests(unittest.TestCase):
    def test_api_key_comparison_accepts_only_matching_nonempty_key(self):
        self.assertTrue(server.api_key_is_valid("secret", "secret"))
        self.assertFalse(server.api_key_is_valid("", "secret"))
        self.assertFalse(server.api_key_is_valid("secret", ""))
        self.assertFalse(server.api_key_is_valid("wrong", "secret"))

    def test_api_key_comparison_trims_whitespace(self):
        self.assertTrue(server.api_key_is_valid("  secret  ", " secret "))


if __name__ == "__main__":
    unittest.main()
