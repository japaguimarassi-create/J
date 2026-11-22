import base64
import json
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

    def make_vault(self, root: Path, password: str):
        vault = root / "vault"
        (vault / "objects").mkdir(parents=True)
        source = root / "original.txt"
        source.write_bytes(b"private AOC file\n")
        salt = b"0123456789abcdef"
        key = agent.derive_key(password, salt)
        object_id = "00000000.bin"
        digest, size = agent.encrypt_stream(source, vault / "objects" / object_id, key,
                                            ("AOC-MIGRATION-FILE-v1:" + object_id).encode())
        metadata = {"format": agent.FORMAT, "cipher": "AES-256-GCM", "kdf": "scrypt",
                    "scrypt_n": agent.SCRYPT_N, "scrypt_r": agent.SCRYPT_R, "scrypt_p": agent.SCRYPT_P,
                    "salt": base64.b64encode(salt).decode()}
        (vault / "vault.json").write_text(json.dumps(metadata), encoding="utf-8")
        manifest = {"format": agent.FORMAT, "roots": ["/home/old-user"],
                    "files": [{"id": object_id, "root": 0, "path": "Documents/test.txt",
                               "size": size, "sha256": digest, "modified_ns": 0}],
                    "errors": [], "source_file_count": 1, "source_bytes": size, "success": True}
        agent.encrypt_manifest(manifest, key, vault / "manifest.enc")
        return vault, source

    def test_full_vault_restore_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault, original = self.make_vault(root, "correct horse battery staple")
            target = root / "restored"
            result = agent.do_restore(str(vault), str(target), "correct horse battery staple")
            restored = target / "01_old-user" / "Documents" / "test.txt"
            self.assertTrue(result["success"])
            self.assertEqual(restored.read_bytes(), original.read_bytes())
            self.assertTrue((target / "AOC_RESTORE_REPORT.json").is_file())

    def test_wrong_password_blocks_restore_without_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault, _ = self.make_vault(root, "correct horse battery staple")
            target = root / "restored"
            with self.assertRaises(Exception):
                agent.do_restore(str(vault), str(target), "wrong horse battery staple")
            self.assertFalse(target.exists())

    def test_restore_refuses_existing_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault, _ = self.make_vault(root, "correct horse battery staple")
            target = root / "existing"
            target.mkdir()
            (target / "keep.txt").write_text("keep", encoding="utf-8")
            with self.assertRaises(ValueError):
                agent.do_restore(str(vault), str(target), "correct horse battery staple")
            self.assertEqual((target / "keep.txt").read_text(encoding="utf-8"), "keep")


if __name__ == "__main__":
    unittest.main()
