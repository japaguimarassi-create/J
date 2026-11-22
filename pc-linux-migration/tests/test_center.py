import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

CENTER = Path(__file__).resolve().parents[1] / "center"
sys.path.insert(0, str(CENTER))
import agent


class EncryptedVaultTests(unittest.TestCase):
    def test_encrypt_verify_and_manifest_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.bin"
            encrypted = root / "encrypted.bin"
            source.write_bytes(b"AOC migration test" * 1000)
            key = agent.derive_key("correct horse battery staple", b"0123456789abcdef")
            digest, size = agent.encrypt_stream(source, encrypted, key, b"test-object")
            self.assertEqual(size, source.stat().st_size)
            self.assertTrue(agent.verify_stream(encrypted, key, b"test-object", digest, size))
            agent.encrypt_manifest({"files": [{"name": "private-name"}]}, key, root / "manifest.enc")
            self.assertEqual(agent.decrypt_manifest(root / "manifest.enc", key)["files"][0]["name"], "private-name")

    def test_tampered_ciphertext_fails_authentication(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.bin"
            encrypted = root / "encrypted.bin"
            source.write_bytes(b"secret data")
            key = agent.derive_key("correct horse battery staple", b"0123456789abcdef")
            digest, size = agent.encrypt_stream(source, encrypted, key, b"test-object")
            data = bytearray(encrypted.read_bytes())
            data[13] ^= 1
            encrypted.write_bytes(data)
            with self.assertRaises(Exception):
                agent.verify_stream(encrypted, key, b"test-object", digest, size)

    def test_short_password_rejected(self):
        with self.assertRaises(ValueError):
            agent.derive_key("short", b"0123456789abcdef")


if __name__ == "__main__":
    unittest.main()
