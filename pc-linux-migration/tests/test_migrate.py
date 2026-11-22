import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "migrate.py"


class MigrationCliTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *map(str, args)],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_backup_verify_and_restore_hidden_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base / "old-profile"
            source.mkdir()
            (source / "photo.txt").write_text("memória", encoding="utf-8")
            hidden = source / ".private"
            hidden.mkdir()
            (hidden / "voice.dat").write_bytes(b"recording-data")
            backup = base / "external" / "MIGRACAO_AOC"

            result = self.run_cli("backup", "--source", source, "--destination", backup)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

            verification = self.run_cli("verify", "--backup", backup)
            self.assertEqual(verification.returncode, 0, verification.stderr + verification.stdout)

            restore = base / "desktop" / "ARQUIVOS_AOC"
            restored = self.run_cli("restore", "--backup", backup, "--destination", restore)
            self.assertEqual(restored.returncode, 0, restored.stderr + restored.stdout)
            self.assertEqual((restore / "001_old-profile" / ".private" / "voice.dat").read_bytes(), b"recording-data")
            self.assertTrue((restore / "RESTORE_REPORT.json").is_file())

    def test_destination_inside_source_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "profile"
            source.mkdir()
            destination = source / "backup"
            result = self.run_cli("backup", "--source", source, "--destination", destination)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("não pode ficar dentro", result.stderr)

    def test_dry_run_does_not_create_destination(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base / "profile"
            source.mkdir()
            (source / "one.bin").write_bytes(b"x")
            destination = base / "not-created"
            result = self.run_cli("backup", "--source", source, "--destination", destination, "--dry-run")
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertFalse(destination.exists())

    def test_manifest_records_sha256(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base / "profile"
            source.mkdir()
            (source / "data.bin").write_bytes(b"abc")
            backup = base / "backup"
            result = self.run_cli("backup", "--source", source, "--destination", backup)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            manifest = json.loads((backup / "MIGRATION_MANIFEST.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["files"][0]["sha256"], "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")


if __name__ == "__main__":
    unittest.main()
