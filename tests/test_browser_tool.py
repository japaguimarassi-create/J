import unittest

from ai.tools.browser import validate_public_url


class BrowserUrlSafetyTests(unittest.TestCase):
    def test_requires_https(self):
        with self.assertRaises(ValueError):
            validate_public_url("http://example.com")

    def test_rejects_credentials_in_url(self):
        with self.assertRaises(ValueError):
            validate_public_url("https://user:password@example.com")

    def test_rejects_localhost_before_network_access(self):
        with self.assertRaises(ValueError):
            validate_public_url("https://localhost")

    def test_rejects_private_ip(self):
        with self.assertRaises(ValueError):
            validate_public_url("https://127.0.0.1")

    def test_rejects_non_web_schemes(self):
        for url in ("file:///etc/passwd", "javascript:alert(1)", "data:text/html,hello"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_public_url(url)


if __name__ == "__main__":
    unittest.main()
